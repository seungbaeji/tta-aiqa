"""Platform SDK unit tests without FastAPI, Alloy, or an OTLP endpoint."""

from __future__ import annotations

import io
import json

import pytest
from aiqa_observability import (
    MetricKind,
    MetricSpec,
    TelemetryContext,
    TelemetryLogLevel,
    TelemetryPolicy,
    create_telemetry,
    derive_telemetry_context,
)
from aiqa_observability.adapters.opentelemetry import normalize_traces_endpoint


def telemetry(stream: io.StringIO):
    return create_telemetry(
        service_name="unit-test-app",
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", TelemetryLogLevel.INFO),
        log_stream=stream,
    )


def test_run_scope_binds_context_emits_json_and_restores_previous_context() -> None:
    stream = io.StringIO()
    runtime = telemetry(stream)
    try:
        assert runtime.current_context() is None
        with runtime.run_scope(
            "model.train",
            run_id="run-123",
            scenario="baseline",
            attributes={"command": "bootstrap"},
        ):
            context = runtime.current_context()
            assert context is not None
            assert context.run_id == "run-123"
            runtime.event(
                "model.training.completed", attributes={"model_profile": "baseline"}
            )
            trace_id, span_id = runtime.tracing.current_ids()
            assert trace_id is not None
            assert span_id is not None
            assert "traceparent" in runtime.outbound_request_headers("X-Request-ID")
        assert runtime.current_context() is None
    finally:
        runtime.shutdown()

    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    completed = next(
        item for item in events if item["event"] == "model.training.completed"
    )
    assert completed["service_name"] == "unit-test-app"
    assert completed["environment"] == "test"
    assert completed["operation"] == "model.train"
    assert completed["run_id"] == "run-123"
    assert completed["scenario"] == "baseline"
    assert completed["model_profile"] == "baseline"
    assert completed["trace_id"]
    assert completed["span_id"]


def test_metric_spec_rejects_correlation_identifiers_as_labels() -> None:
    with pytest.raises(ValueError, match="forbidden metric labels"):
        MetricSpec(
            name="aiqa_bad_total",
            description="invalid metric",
            kind=MetricKind.COUNTER,
            labels=("service_name", "trace_id"),
        )


@pytest.mark.parametrize(
    ("name", "labels", "message"),
    [
        ("invalid-metric", ("service_name",), "metric name"),
        ("aiqa_valid_total", ("invalid-label",), "metric labels"),
        ("aiqa_valid_total", ("le",), "cannot include le"),
    ],
)
def test_metric_spec_rejects_invalid_prometheus_declarations(
    name: str, labels: tuple[str, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        MetricSpec(
            name=name,
            description="invalid metric",
            kind=MetricKind.HISTOGRAM,
            labels=labels,
            buckets=(0.1, 1.0),
        )


def test_metric_registry_exposes_only_declared_bounded_labels() -> None:
    stream = io.StringIO()
    runtime = telemetry(stream)
    try:
        requests = runtime.counter(
            MetricSpec(
                name="aiqa_unit_requests_total",
                description="unit requests",
                kind=MetricKind.COUNTER,
                labels=("service_name", "operation"),
            )
        )
        requests.increment(
            labels={"service_name": "unit-test-app", "operation": "model.train"}
        )
        metrics = runtime.render_metrics().decode()
    finally:
        runtime.shutdown()

    assert 'operation="model.train"' in metrics
    assert "run-123" not in metrics
    assert "trace_id" not in metrics


def test_metric_handle_rejects_missing_or_extra_label_values() -> None:
    runtime = telemetry(io.StringIO())
    try:
        requests = runtime.counter(
            MetricSpec(
                name="aiqa_unit_label_contract_total",
                description="unit label contract",
                kind=MetricKind.COUNTER,
                labels=("service_name", "operation"),
            )
        )
        with pytest.raises(ValueError, match="labels do not match"):
            requests.increment(labels={"service_name": "unit-test-app"})
        with pytest.raises(ValueError, match="labels do not match"):
            requests.increment(
                labels={
                    "service_name": "unit-test-app",
                    "operation": "model.train",
                    "request_id": "forbidden",
                }
            )
    finally:
        runtime.shutdown()


def test_shutdown_is_idempotent() -> None:
    runtime = telemetry(io.StringIO())

    runtime.shutdown()
    runtime.shutdown()


def test_derived_context_inherits_correlation_values_and_merges_attributes() -> None:
    parent = TelemetryContext.create(
        operation="http.request",
        request_id="request-1",
        scenario="baseline",
        attributes={"route": "/v1/predict", "status_code": 200},
    )

    child = derive_telemetry_context(
        parent,
        operation="model.score",
        attributes={"status_code": 422, "model_profile": "candidate-b"},
    )

    assert child.request_id == "request-1"
    assert child.scenario == "baseline"
    assert child.as_log_fields() == {
        "operation": "model.score",
        "request_id": "request-1",
        "scenario": "baseline",
        "route": "/v1/predict",
        "status_code": 422,
        "model_profile": "candidate-b",
    }


def test_otlp_traces_endpoint_is_normalized_once() -> None:
    assert normalize_traces_endpoint("https://otlp.example") == (
        "https://otlp.example/v1/traces"
    )
    assert normalize_traces_endpoint("https://otlp.example/v1/traces/") == (
        "https://otlp.example/v1/traces"
    )
