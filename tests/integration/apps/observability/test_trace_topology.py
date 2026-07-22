"""Cross-adapter trace topology and noise-control contracts."""

from __future__ import annotations

import io
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
from traffic_generator.adapters import RequestsPredictionClient


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


def telemetry(service_name: str) -> Telemetry:
    """Build an isolated telemetry runtime with silent structured logs."""
    return create_telemetry(
        service_name=service_name,
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", TelemetryLogLevel.INFO),
        log_stream=io.StringIO(),
    )


def exporter(runtime: Telemetry) -> InMemorySpanExporter:
    """Attach a synchronous in-memory exporter to one test-local provider."""
    collector = InMemorySpanExporter()
    runtime.tracing.provider.add_span_processor(SimpleSpanProcessor(collector))
    return collector


def risk_api() -> tuple[TestClient, Telemetry]:
    """Build the real Risk API HTTP adapter around a deterministic scorer."""
    platform = telemetry("risk-api")
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
        with api, traffic_runtime.run_scope("traffic.generate", scenario="baseline"):
            response = client.predict(
                features={"age": 42.0},
                request_id="baseline-42-0001",
                scenario="baseline",
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
