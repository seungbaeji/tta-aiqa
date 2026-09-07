"""Traffic configuration and V2 patient pool adapter tests."""

import io
import json
from pathlib import Path

import pytest
from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import (
    TelemetryLogLevel,
    TelemetryPolicy,
    create_telemetry,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind
from pydantic import ValidationError
from traffic_generator.adapters import (
    CsvPatientPool,
    JsonCollectionSessionRecorder,
    RequestsPredictionClient,
    load_traffic_config,
)
from traffic_generator.domain import (
    CollectionModelIdentity,
    CollectionSession,
    ScenarioCollection,
    ScenarioMode,
)


class CapturingResponse:
    """Minimal successful HTTP response returned by the prediction-client fake."""

    status_code = 200
    text = "{}"

    def json(self) -> dict[str, object]:
        return {}


class CapturingSession:
    """Capture request headers without making an outbound HTTP call."""

    def __init__(self) -> None:
        self.headers: dict[str, str] | None = None

    def post(
        self,
        _url: str,
        *,
        json: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> CapturingResponse:
        assert json == {"features": {"age": 42.0}}
        assert timeout == 1.0
        self.headers = headers
        return CapturingResponse()


def telemetry():
    """Build an isolated runtime whose spans can be asserted in this test module."""
    return create_telemetry(
        service_name="traffic-generator",
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", TelemetryLogLevel.INFO),
        log_stream=io.StringIO(),
    )


def test_versioned_config_defines_all_four_course_scenarios() -> None:
    config = load_traffic_config(Path("configs/traffic/scenarios.yaml"))
    plans = config.plans()

    assert set(plans) == {
        "baseline",
        "approved-candidate",
        "current-shift",
        "invalid",
    }
    assert plans["baseline"].mode is ScenarioMode.VALID
    assert plans["current-shift"].mode is ScenarioMode.SHIFT
    assert plans["invalid"].mode is ScenarioMode.INVALID
    assert plans["invalid"].request_count == 3
    assert plans["invalid"].interval_seconds == 8.0


def test_v2_operational_pool_is_target_free_and_wire_compatible() -> None:
    contract = load_feature_contract(Path("configs/contracts/model-input.yaml"))
    pool = CsvPatientPool(
        Path("data/splits-v2/operational.csv"),
        contract,
    )

    patient = pool.patient(0)
    assert pool.size == 100
    assert set(patient) == set(contract.feature_names)
    assert isinstance(patient["age__missing"], bool)
    assert "target" not in patient


def test_prediction_client_propagates_trace_context_with_course_headers() -> None:
    """Each traffic request has a CLIENT span and injects its W3C context."""
    runtime = telemetry()
    exporter = InMemorySpanExporter()
    runtime.tracing.provider.add_span_processor(SimpleSpanProcessor(exporter))
    session = CapturingSession()
    client = RequestsPredictionClient(
        "http://risk-api.example",
        telemetry=runtime,
        session=session,  # type: ignore[arg-type]
    )

    try:
        with runtime.run_scope(
            "traffic.generate",
            run_id="course-run",
            scenario="baseline",
        ):
            response = client.predict(
                features={"age": 42.0},
                request_id="baseline-course-run-0001",
                run_id="course-run",
                scenario="baseline",
                timeout_seconds=1.0,
            )
    finally:
        runtime.shutdown()

    assert response.status_code == 200
    assert session.headers is not None
    assert {
        name: value for name, value in session.headers.items() if name != "traceparent"
    } == {
        "X-Request-ID": "baseline-course-run-0001",
        "X-AIQA-Run-ID": "course-run",
        "X-AIQA-Scenario": "baseline",
    }
    assert response.run_id == "course-run"
    client_span = next(
        span
        for span in exporter.get_finished_spans()
        if span.name == "risk-api.predict"
    )
    root_span = next(
        span
        for span in exporter.get_finished_spans()
        if span.name == "traffic.generate"
    )
    traceparent = session.headers["traceparent"].split("-")

    assert client_span.kind is SpanKind.CLIENT
    assert client_span.parent is not None
    assert client_span.parent.span_id == root_span.context.span_id
    assert traceparent[1] == f"{client_span.context.trace_id:032x}"
    assert traceparent[2] == f"{client_span.context.span_id:016x}"


def test_session_manifest_recorder_writes_one_deterministic_document(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "collection-session.json"
    session = CollectionSession(
        session_id="session-01",
        started_at="2026-07-27T05:00:00Z",
        completed_at="2026-07-27T05:03:00Z",
        environment="compose",
        scope="local",
        model_identity=CollectionModelIdentity(
            profile="baseline",
            version="baseline-f2576f12512a",
            threshold=0.5,
        ),
        manifest_path=Path("artifacts/traffic/collection-session.json"),
        scenarios=tuple(
            ScenarioCollection(
                name=name,
                run_id=f"session-01-{name}",
                started_at=f"2026-07-27T05:0{index}:00Z",
                completed_at=f"2026-07-27T05:0{index + 1}:00Z",
                status_counts=((422, 3),) if name == "invalid" else ((200, 20),),
                artifact_path=Path("artifacts/traffic/compose.jsonl"),
            )
            for index, name in enumerate(("baseline", "current-shift", "invalid"))
        ),
    )

    recorder = JsonCollectionSessionRecorder(manifest_path)
    recorder.write(session)

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == (
        session.as_document()
    )
    assert recorder.read() == session
    assert manifest_path.read_text(encoding="utf-8").endswith("\n")
    assert not manifest_path.with_suffix(".json.tmp").exists()


def test_session_manifest_reader_rejects_type_coercion(tmp_path: Path) -> None:
    manifest_path = tmp_path / "collection-session.json"
    session = CollectionSession(
        session_id="session-01",
        started_at="2026-07-27T05:00:00Z",
        completed_at="2026-07-27T05:03:00Z",
        environment="compose",
        scope="local",
        model_identity=CollectionModelIdentity(
            profile="baseline",
            version="baseline-f2576f12512a",
            threshold=0.5,
        ),
        manifest_path=Path("artifacts/traffic/collection-session.json"),
        scenarios=tuple(
            ScenarioCollection(
                name=name,
                run_id=f"session-01-{name}",
                started_at=f"2026-07-27T05:0{index}:00Z",
                completed_at=f"2026-07-27T05:0{index + 1}:00Z",
                status_counts=((422, 3),) if name == "invalid" else ((200, 20),),
                artifact_path=Path("artifacts/traffic/compose.jsonl"),
            )
            for index, name in enumerate(("baseline", "current-shift", "invalid"))
        ),
    )
    recorder = JsonCollectionSessionRecorder(manifest_path)
    recorder.write(session)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(document["model_identity"], dict)
    document["model_identity"]["threshold"] = "0.5"
    manifest_path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        recorder.read()


def test_session_manifest_write_failure_preserves_previous_document(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "collection-session.json"
    previous = '{"session_id":"previous"}\n'
    manifest_path.write_text(previous, encoding="utf-8")
    session = CollectionSession(
        session_id="session-01",
        started_at="2026-07-27T05:00:00Z",
        completed_at="2026-07-27T05:03:00Z",
        environment="compose",
        scope="local",
        model_identity=CollectionModelIdentity(
            profile="baseline",
            version="baseline-f2576f12512a",
            threshold=0.5,
        ),
        manifest_path=Path("artifacts/traffic/collection-session.json"),
        scenarios=tuple(
            ScenarioCollection(
                name=name,
                run_id=f"session-01-{name}",
                started_at=f"2026-07-27T05:0{index}:00Z",
                completed_at=f"2026-07-27T05:0{index + 1}:00Z",
                status_counts=((422, 3),) if name == "invalid" else ((200, 20),),
                artifact_path=Path("artifacts/traffic/compose.jsonl"),
            )
            for index, name in enumerate(("baseline", "current-shift", "invalid"))
        ),
    )

    def fail_replace(_source: Path, _target: Path) -> Path:
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated atomic replace failure"):
        JsonCollectionSessionRecorder(manifest_path).write(session)

    assert manifest_path.read_text(encoding="utf-8") == previous
    assert not manifest_path.with_suffix(".json.tmp").exists()
