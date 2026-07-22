"""Risk API adapter behavior independent from FastAPI and model runtimes."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from aiqa_observability import (
    TelemetryLogLevel,
    TelemetryPolicy,
    TelemetryResource,
    create_telemetry,
)
from aiqa_serving.domain import FeatureValue, ModelIdentity, PredictionEvent
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind
from risk_api.adapters.kserve_tracing import KServeTracingScorer
from risk_api.adapters.metadata import load_kserve_model_identity
from risk_api.adapters.metric_labels import (
    prediction_metric_labels,
    request_metric_labels,
)


def write_deployed_metadata(path: Path, *, contract_sha256: str) -> None:
    """Write the minimal deployed metadata required by the KServe runtime adapter."""
    path.write_text(
        json.dumps(
            {
                "profile": "candidate-b",
                "threshold": 0.35,
                "model_sha256": "a" * 64,
                "feature_contract": {"sha256": contract_sha256},
            }
        ),
        encoding="utf-8",
    )


def telemetry_resource() -> TelemetryResource:
    """Return a stable process resource for bounded metric label assertions."""
    return TelemetryResource(
        service_name="risk-api",
        service_namespace="tta-aiqa",
        environment="compose",
    )


def prediction_event() -> PredictionEvent:
    """Return one serving event with fields that must become bounded labels."""
    return PredictionEvent(
        request_id="request-123",
        model_profile="candidate-b",
        model_version="candidate-b-aaaaaaaaaaaa",
        score=0.73,
        threshold=0.35,
        prediction="high_risk",
        missing_feature_count=2,
        scenario="baseline",
    )


class CapturingKServeScorer:
    """Expose the propagated header captured at the delegated scoring boundary."""

    identity = ModelIdentity("candidate-b", "candidate-b-test", 0.35)

    def __init__(self, headers_provider) -> None:
        self._headers_provider = headers_provider
        self.headers: dict[str, str] | None = None

    def ready(self) -> bool:
        """Report the deterministic test backend as ready."""
        return True

    def score(self, _features: tuple[tuple[str, FeatureValue], ...]) -> float:
        """Capture the trace context that a concrete KServe adapter would send."""
        self.headers = self._headers_provider()
        return 0.8


def test_kserve_metadata_adapter_requires_the_mounted_feature_contract(
    tmp_path: Path,
) -> None:
    """KServe identity is derived only from validated deployed metadata evidence."""
    metadata_path = tmp_path / "metadata.json"
    contract_sha256 = "b" * 64
    write_deployed_metadata(metadata_path, contract_sha256=contract_sha256)

    identity = load_kserve_model_identity(
        metadata_path,
        expected_feature_contract_sha256=contract_sha256,
    )

    assert identity.profile == "candidate-b"
    assert identity.version == "candidate-b-aaaaaaaaaaaa"
    assert identity.threshold == 0.35
    with pytest.raises(ValueError, match="feature contract hash mismatch"):
        load_kserve_model_identity(
            metadata_path,
            expected_feature_contract_sha256="c" * 64,
        )


def test_metric_label_adapters_exclude_unbounded_request_identifiers() -> None:
    """Metric labels use only process identity and bounded request/model state."""
    request_labels = request_metric_labels(
        telemetry_resource(),
        route="/v1/predict",
        method="POST",
        status_code=200,
    )
    prediction_labels = prediction_metric_labels(
        telemetry_resource(),
        event=prediction_event(),
        scenario="baseline",
    )

    assert request_labels == {
        "service_name": "risk-api",
        "environment": "compose",
        "route": "/v1/predict",
        "method": "POST",
        "status_code": "200",
    }
    assert prediction_labels == {
        "service_name": "risk-api",
        "environment": "compose",
        "model_profile": "candidate-b",
        "model_version": "candidate-b-aaaaaaaaaaaa",
        "scenario": "baseline",
        "prediction": "high_risk",
    }
    assert "request_id" not in request_labels | prediction_labels


def test_kserve_tracing_scorer_creates_client_span_and_propagates_context() -> None:
    """The outbound KServe call is a child CLIENT span, not only a header hop."""
    runtime = create_telemetry(
        service_name="risk-api",
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", TelemetryLogLevel.INFO),
        log_stream=io.StringIO(),
    )
    exporter = InMemorySpanExporter()
    runtime.tracing.provider.add_span_processor(SimpleSpanProcessor(exporter))
    delegate = CapturingKServeScorer(runtime.outbound_trace_headers)
    scorer = KServeTracingScorer(
        delegate,
        telemetry=runtime,
        model_name="mortality-risk",
    )

    try:
        with runtime.operation_scope("risk.predict"):
            assert scorer.score((("age", 67.0),)) == 0.8
    finally:
        runtime.shutdown()

    parent_span = next(
        span for span in exporter.get_finished_spans() if span.name == "risk.predict"
    )
    client_span = next(
        span for span in exporter.get_finished_spans() if span.name == "kserve.infer"
    )

    assert delegate.headers is not None
    traceparent = delegate.headers["traceparent"].split("-")
    assert client_span.kind is SpanKind.CLIENT
    assert client_span.parent is not None
    assert client_span.parent.span_id == parent_span.context.span_id
    assert traceparent[1] == f"{client_span.context.trace_id:032x}"
    assert traceparent[2] == f"{client_span.context.span_id:016x}"
