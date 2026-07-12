"""Platform SDK unit tests without FastAPI, Alloy, or an OTLP endpoint."""

from __future__ import annotations

import io
import json

import pytest
from aiqa_observability import (
    MetricKind,
    MetricSpec,
    TelemetryPolicy,
    create_telemetry,
    current_context,
)


def telemetry(stream: io.StringIO):
    return create_telemetry(
        service_name="unit-test-app",
        environment="test",
        policy=TelemetryPolicy(2, "tta-aiqa", "INFO"),
        log_stream=stream,
    )


def test_run_scope_binds_context_emits_json_and_restores_previous_context() -> None:
    stream = io.StringIO()
    runtime = telemetry(stream)
    try:
        assert current_context() is None
        with runtime.run_scope(
            "model.train",
            run_id="run-123",
            scenario="baseline",
            attributes={"command": "bootstrap"},
        ):
            context = current_context()
            assert context is not None
            assert context.run_id == "run-123"
            runtime.event(
                "model.training.completed", attributes={"model_profile": "baseline"}
            )
            trace_id, span_id = runtime.tracing.current_ids()
            assert trace_id is not None
            assert span_id is not None
            assert "traceparent" in runtime.outbound_trace_headers()
        assert current_context() is None
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
        requests.labels(service_name="unit-test-app", operation="model.train").inc()
        metrics = runtime.render_metrics().decode()
    finally:
        runtime.shutdown()

    assert 'operation="model.train"' in metrics
    assert "run-123" not in metrics
    assert "trace_id" not in metrics


def test_shutdown_is_idempotent() -> None:
    runtime = telemetry(io.StringIO())

    runtime.shutdown()
    runtime.shutdown()
