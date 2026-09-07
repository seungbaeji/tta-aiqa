"""Cross-adapter trace topology and noise-control contracts."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from aiqa_observability import (
    Telemetry,
    TelemetryLogLevel,
    TelemetryPolicy,
    create_telemetry,
)
from aiqa_observability.adapters import instrument_fastapi
from aiqa_serving.domain import FeatureValue, ModelIdentity, RiskPrediction, ScoredRisk
from fastapi import FastAPI
from fastapi.testclient import TestClient
from kserve_predictor.adapters import (
    KSERVE_TRACE_EXCLUDED_URLS,
)
from kserve_predictor.adapters import (
    build_http_app as build_kserve_http_app,
)
from opentelemetry import context
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind
from risk_api.adapters import (
    RISK_API_TRACE_EXCLUDED_URLS,
    RiskApiTelemetry,
    build_http_app,
    load_api_config,
)
from traffic_generator.adapters import JsonlTrafficRecorder, RequestsPredictionClient
from traffic_generator.application import build_request_id


class StubScorer:
    """Minimal local scorer used only to exercise the Risk API HTTP boundary."""

    identity = ModelIdentity("baseline", "baseline-test", 0.5)

    def ready(self) -> bool:
        """Report the fixed local model as ready."""
        return True

    def score(self, _features: tuple[tuple[str, FeatureValue], ...]) -> float:
        """Return one deterministic score through the serving scorer port."""
        return 0.8


class RiskApiTestSession:
    """Route requests through TestClient while preserving the outbound headers."""

    def __init__(self, api: TestClient) -> None:
        self._api = api

    def post(
        self,
        url: str,
        *,
        json: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> Any:
        """Adapt requests.Session while simulating the outbound process boundary."""
        assert url == "http://risk-api.test/v1/predict"
        assert timeout == 1.0
        token = context.attach(context.Context())
        try:
            return self._api.post("/v1/predict", json=json, headers=headers)
        finally:
            context.detach(token)


def telemetry(service_name: str, *, log_stream: io.StringIO | None = None) -> Telemetry:
    """Build an isolated telemetry runtime with silent structured logs."""
    return create_telemetry(
        service_name=service_name,
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", TelemetryLogLevel.INFO),
        log_stream=log_stream or io.StringIO(),
    )


def exporter(runtime: Telemetry) -> InMemorySpanExporter:
    """Attach a synchronous in-memory exporter to one test-local provider."""
    collector = InMemorySpanExporter()
    runtime.tracing.provider.add_span_processor(SimpleSpanProcessor(collector))
    return collector


def risk_api(
    *, log_stream: io.StringIO | None = None
) -> tuple[TestClient, Telemetry]:
    """Build the real Risk API HTTP adapter around a deterministic scorer."""
    platform = telemetry("risk-api", log_stream=log_stream)
    config = load_api_config(Path("configs/serving/api.yaml"))
    scorer = StubScorer()
    app: FastAPI = build_http_app(
        config=config,
        feature_count=2,
        predict_operation=lambda request: RiskPrediction(
            request_id=request.request_id,
            model=scorer.identity,
            score=0.8,
            label="high_risk",
        ),
        scorer=scorer,
        backend="local",
        telemetry=RiskApiTelemetry(platform, config.observability),
    )
    instrument_fastapi(
        app,
        platform.tracing,
        excluded_urls=RISK_API_TRACE_EXCLUDED_URLS,
    )
    return TestClient(app), platform


def kserve_api() -> tuple[TestClient, Telemetry]:
    """Build the real KServe HTTP adapter around the deterministic scorer."""
    platform = telemetry("kserve-risk-predictor")
    scorer = StubScorer()
    app: FastAPI = build_kserve_http_app(
        model_name="mortality-risk",
        score_operation=lambda request: ScoredRisk(
            request_id=request.request_id,
            model=scorer.identity,
            score=0.8,
            missing_feature_count=0,
        ),
        scorer=scorer,
        telemetry=platform,
    )
    instrument_fastapi(
        app,
        platform.tracing,
        excluded_urls=KSERVE_TRACE_EXCLUDED_URLS,
    )
    return TestClient(app), platform


def span_by_name(exporter: InMemorySpanExporter, name: str):
    """Return the unique finished span with the expected operation name."""
    matches = [span for span in exporter.get_finished_spans() if span.name == name]
    assert len(matches) == 1
    return matches[0]


def test_trace_topology_links_traffic_client_to_risk_api_prediction() -> None:
    """A generated request is one trace across CLIENT, SERVER, and operation spans."""
    api, api_runtime = risk_api()
    api_exporter = exporter(api_runtime)
    traffic_runtime = telemetry("traffic-generator")
    traffic_exporter = exporter(traffic_runtime)
    client = RequestsPredictionClient(
        "http://risk-api.test",
        telemetry=traffic_runtime,
        session=RiskApiTestSession(api),  # type: ignore[arg-type]
    )

    try:
        with api, traffic_runtime.run_scope(
            "traffic.generate",
            run_id="trace-run",
            scenario="baseline",
        ):
            response = client.predict(
                features={"age": 42.0},
                request_id="baseline-trace-run-0001",
                run_id="trace-run",
                scenario="baseline",
                record_id="132648",
                timeout_seconds=1.0,
            )
    finally:
        traffic_runtime.shutdown()

    traffic_root = span_by_name(traffic_exporter, "traffic.generate")
    client_span = span_by_name(traffic_exporter, "risk-api.predict")
    server_span = span_by_name(api_exporter, "POST /v1/predict")
    prediction_span = span_by_name(api_exporter, "risk.predict")

    assert response.status_code == 200
    assert client_span.kind is SpanKind.CLIENT
    assert server_span.kind is SpanKind.SERVER
    assert client_span.parent is not None
    assert server_span.parent is not None
    assert prediction_span.parent is not None
    assert client_span.parent.span_id == traffic_root.context.span_id
    assert server_span.parent.span_id == client_span.context.span_id
    assert prediction_span.parent.span_id == server_span.context.span_id
    assert len(
        {
            traffic_root.context.trace_id,
            client_span.context.trace_id,
            server_span.context.trace_id,
            prediction_span.context.trace_id,
        }
    ) == 1
    assert traffic_root.attributes["aiqa.run_id"] == "trace-run"
    assert client_span.attributes["aiqa.run_id"] == "trace-run"
    assert server_span.attributes["aiqa.run_id"] == "trace-run"
    assert prediction_span.attributes["aiqa.run_id"] == "trace-run"
    assert server_span.attributes["aiqa.scenario"] == "baseline"
    assert prediction_span.attributes["aiqa.scenario"] == "baseline"


def test_max_run_id_stays_correlated_across_client_jsonl_and_server_logs(
    tmp_path: Path,
) -> None:
    """A maximum-length run ID never makes the server replace its request ID."""
    api_stream = io.StringIO()
    api, api_runtime = risk_api(log_stream=api_stream)
    api_exporter = exporter(api_runtime)
    traffic_runtime = telemetry("traffic-generator")
    client = RequestsPredictionClient(
        "http://risk-api.test",
        telemetry=traffic_runtime,
        session=RiskApiTestSession(api),  # type: ignore[arg-type]
    )
    recorder = JsonlTrafficRecorder(tmp_path / "traffic-responses.jsonl")
    run_id = f"{'r' * 63}a"
    request_id = build_request_id(
        scenario="baseline",
        run_id=run_id,
        sequence=1,
    )

    try:
        with api, traffic_runtime.run_scope(
            "traffic.generate",
            run_id=run_id,
            scenario="baseline",
        ):
            response = client.predict(
                features={"age": 42.0},
                request_id=request_id,
                run_id=run_id,
                scenario="baseline",
                record_id="132648",
                timeout_seconds=1.0,
            )
            recorder.record(response)
    finally:
        traffic_runtime.shutdown()

    evidence = json.loads(
        (tmp_path / "traffic-responses.jsonl").read_text(encoding="utf-8")
    )
    events = [
        json.loads(line)
        for line in api_stream.getvalue().splitlines()
        if line.strip()
    ]
    completion = next(
        event for event in events if event["event"] == "http.request.completed"
    )
    server_span = span_by_name(api_exporter, "POST /v1/predict")
    prediction_span = span_by_name(api_exporter, "risk.predict")

    assert response.status_code == 200
    assert len(request_id) == 64
    assert evidence["request_id"] == request_id
    assert evidence["record_id"] == "132648"
    assert evidence["body"]["request_id"] == request_id
    assert completion["request_id"] == request_id
    assert completion["run_id"] == run_id
    assert completion["record_id"] == "132648"
    assert server_span.attributes["aiqa.request_id"] == request_id
    assert prediction_span.attributes["aiqa.request_id"] == request_id
    assert server_span.attributes["aiqa.record_id"] == "132648"
    assert prediction_span.attributes["aiqa.record_id"] == "132648"


def test_risk_api_excludes_probe_and_scrape_spans() -> None:
    """Probe and scrape routes must not consume trace volume or create ASGI noise."""
    api, runtime = risk_api()
    collector = exporter(runtime)

    with api:
        assert api.get("/health/live").status_code == 200
        assert api.get("/health/ready").status_code == 200
        assert api.get("/metrics").status_code == 200
        assert (
            api.post(
                "/v1/predict",
                json={"features": {"age": 42.0}},
            ).status_code
            == 200
        )

    span_names = {span.name for span in collector.get_finished_spans()}

    assert span_names == {"POST /v1/predict", "risk.predict"}


def test_input_error_logs_and_spans_contain_only_bounded_details() -> None:
    """A rejected payload remains diagnosable without copying internal raw details."""
    stream = io.StringIO()
    platform = create_telemetry(
        service_name="risk-api",
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", TelemetryLogLevel.INFO),
        log_stream=stream,
    )
    collector = exporter(platform)
    config = load_api_config(Path("configs/serving/api.yaml"))
    scorer = StubScorer()

    def reject_input(_request):
        raise ValueError(
            "boolean feature has invalid type: sensitive_internal_feature_name"
        )

    app = build_http_app(
        config=config,
        feature_count=2,
        predict_operation=reject_input,
        scorer=scorer,
        backend="local",
        telemetry=RiskApiTelemetry(platform, config.observability),
    )
    instrument_fastapi(
        app,
        platform.tracing,
        excluded_urls=RISK_API_TRACE_EXCLUDED_URLS,
    )

    with TestClient(app) as api:
        response = api.post(
            "/v1/predict",
            headers={
                "X-Request-ID": "invalid-course-run-0001",
                "X-AIQA-Run-ID": "course-run",
                "X-AIQA-Scenario": "invalid",
            },
            json={"features": {"age": 42.0}},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "MODEL_INPUT_INVALID",
        "validation_category": "type",
        "message": "model input does not match the public contract",
    }
    events = [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if line.strip()
    ]
    failure = next(
        event
        for event in events
        if event["event"] == "model.input.validation.failed"
    )
    assert failure["error_code"] == "MODEL_INPUT_INVALID"
    assert failure["validation_category"] == "type"
    assert failure["run_id"] == "course-run"
    assert failure["request_id"] == "invalid-course-run-0001"
    prediction_span = span_by_name(collector, "risk.predict")
    assert prediction_span.attributes["aiqa.error_code"] == "MODEL_INPUT_INVALID"
    assert prediction_span.attributes["aiqa.validation_category"] == "type"
    serialized_spans = str(
        [
            (span.attributes, [(event.name, event.attributes) for event in span.events])
            for span in collector.get_finished_spans()
        ]
    )
    assert "sensitive_internal_feature_name" not in stream.getvalue()
    assert "sensitive_internal_feature_name" not in serialized_spans


def test_framework_validation_logs_and_spans_contain_only_bounded_details() -> None:
    """DTO rejection creates prediction telemetry without copying the raw body."""
    stream = io.StringIO()
    platform = create_telemetry(
        service_name="risk-api",
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", TelemetryLogLevel.INFO),
        log_stream=stream,
    )
    collector = exporter(platform)
    config = load_api_config(Path("configs/serving/api.yaml"))
    scorer = StubScorer()
    app = build_http_app(
        config=config,
        feature_count=2,
        predict_operation=lambda request: RiskPrediction(
            request_id=request.request_id,
            model=scorer.identity,
            score=0.8,
            label="high_risk",
        ),
        scorer=scorer,
        backend="local",
        telemetry=RiskApiTelemetry(platform, config.observability),
    )
    instrument_fastapi(
        app,
        platform.tracing,
        excluded_urls=RISK_API_TRACE_EXCLUDED_URLS,
    )
    sentinel = "raw-pydantic-input-must-stay-private"

    with TestClient(app) as api:
        response = api.post(
            "/v1/predict",
            headers={
                "X-Request-ID": "framework-validation-0001",
                "X-AIQA-Run-ID": "course-run",
                "X-AIQA-Scenario": "invalid",
            },
            json={"features": sentinel},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "MODEL_INPUT_INVALID",
        "validation_category": "type",
        "message": "model input does not match the public contract",
    }
    events = [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if line.strip()
    ]
    failure = next(
        event
        for event in events
        if event["event"] == "model.input.validation.failed"
    )
    assert failure["error_code"] == "MODEL_INPUT_INVALID"
    assert failure["validation_category"] == "type"
    assert failure["run_id"] == "course-run"
    assert failure["request_id"] == "framework-validation-0001"
    prediction_span = span_by_name(collector, "risk.predict")
    assert prediction_span.attributes["aiqa.error_code"] == "MODEL_INPUT_INVALID"
    assert prediction_span.attributes["aiqa.validation_category"] == "type"
    serialized_spans = str(
        [
            (span.attributes, [(event.name, event.attributes) for event in span.events])
            for span in collector.get_finished_spans()
        ]
    )
    assert sentinel not in str(response.json())
    assert sentinel not in stream.getvalue()
    assert sentinel not in serialized_spans


def test_oversized_body_emits_only_a_bounded_rejection_event() -> None:
    """A 413 remains observable without copying any attacker-controlled body."""
    stream = io.StringIO()
    platform = create_telemetry(
        service_name="risk-api",
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", TelemetryLogLevel.INFO),
        log_stream=stream,
    )
    collector = exporter(platform)
    config = load_api_config(Path("configs/serving/api.yaml"))
    scorer = StubScorer()
    app = build_http_app(
        config=config,
        feature_count=2,
        predict_operation=lambda request: RiskPrediction(
            request_id=request.request_id,
            model=scorer.identity,
            score=0.8,
            label="high_risk",
        ),
        scorer=scorer,
        backend="local",
        telemetry=RiskApiTelemetry(platform, config.observability),
    )
    instrument_fastapi(
        app,
        platform.tracing,
        excluded_urls=RISK_API_TRACE_EXCLUDED_URLS,
    )
    sentinel = "attacker-controlled-payload"

    with TestClient(app) as api:
        response = api.post(
            "/v1/predict",
            headers={
                "X-Request-ID": "x" * 65,
                "X-AIQA-Run-ID": "unsafe/run/id",
            },
            json={"features": {"age": sentinel * 4_000}},
        )

    assert response.status_code == 413
    events = [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if line.strip()
    ]
    rejection = next(
        event for event in events if event["event"] == "http.request.rejected"
    )
    assert rejection["error_code"] == "REQUEST_BODY_TOO_LARGE"
    assert rejection["rejection_category"] == "body_too_large"
    assert len(rejection["request_id"]) == 36
    assert "run_id" not in rejection
    server_span = span_by_name(collector, "POST /v1/predict")
    assert server_span.attributes["aiqa.error_code"] == "REQUEST_BODY_TOO_LARGE"
    assert server_span.attributes["aiqa.rejection_category"] == "body_too_large"
    assert sentinel not in stream.getvalue()
    assert "x" * 65 not in stream.getvalue()
    assert "unsafe/run/id" not in stream.getvalue()


def test_kserve_excludes_readiness_spans_but_traces_inference() -> None:
    """KServe keeps useful inference spans while dropping routine probe traffic."""
    api, runtime = kserve_api()
    collector = exporter(runtime)

    with api:
        assert api.get("/v2/health/live").status_code == 200
        assert api.get("/v2/health/ready").status_code == 200
        assert api.get("/v2/models/mortality-risk/ready").status_code == 200
        assert (
            api.post(
                "/v2/models/mortality-risk/infer",
                json={
                    "id": "trace-contract-1",
                    "inputs": [
                        {
                            "name": "features",
                            "shape": [1],
                            "datatype": "BYTES",
                            "data": ['{"age":42.0}'],
                        }
                    ],
                },
            ).status_code
            == 200
        )

    span_names = {span.name for span in collector.get_finished_spans()}

    assert "kserve.infer" in span_names
    assert not any("health" in name or "ready" in name for name in span_names)
    assert not any(name.endswith("http receive") for name in span_names)
    assert not any(name.endswith("http send") for name in span_names)
