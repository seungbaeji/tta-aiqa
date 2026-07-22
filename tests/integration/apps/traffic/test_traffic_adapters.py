"""Traffic configuration and V2 patient pool adapter tests."""

import io
from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import (
    TelemetryLogLevel,
    TelemetryPolicy,
    create_telemetry,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind
from traffic_generator.adapters import (
    CsvPatientPool,
    RequestsPredictionClient,
    load_traffic_config,
)
from traffic_generator.domain import ScenarioMode


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


def test_v2_operational_pool_is_target_free_and_wire_compatible() -> None:
    contract = load_feature_contract(Path("configs/contracts/model-input.yaml"))
    pool = CsvPatientPool(
        Path("data/splits/physionet-2012/revisions/v2/datasets/operational.csv"),
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
        with runtime.run_scope("traffic.generate", scenario="baseline"):
            response = client.predict(
                features={"age": 42.0},
                request_id="baseline-43-0001",
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
        "X-Request-ID": "baseline-43-0001",
        "X-AIQA-Scenario": "baseline",
    }
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
