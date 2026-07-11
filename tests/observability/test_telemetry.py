"""Telemetry contract and Risk API signal tests."""

from pathlib import Path

import pytest
from aiqa_observability.adapters import TelemetryRuntime, load_telemetry_contract
from aiqa_observability.domain import PredictionObservation, TelemetryContract


def test_contract_forbids_request_id_metric_cardinality() -> None:
    contract = load_telemetry_contract(Path("configs/observability/telemetry.yaml"))
    assert "request_id" not in contract.labels.request_metrics
    assert "request_id" not in contract.labels.prediction_metrics
    assert contract.labels.logs_and_traces == ("request_id",)


def test_runtime_exposes_bounded_prediction_metrics() -> None:
    contract = load_telemetry_contract(Path("configs/observability/telemetry.yaml"))
    runtime = TelemetryRuntime(contract, "test")

    runtime.record_prediction(
        PredictionObservation(
            request_id="request-1",
            model_profile="candidate-b",
            model_version="candidate-b-123",
            score=0.72,
            threshold=0.35,
            prediction="high_risk",
            missing_feature_count=2,
            scenario="current-shift",
            trace_id="abc123",
        )
    )
    metrics = runtime.render_metrics().decode()

    assert contract.metrics.prediction_count in metrics
    assert 'model_profile="candidate-b"' in metrics
    assert 'scenario="current-shift"' in metrics
    assert "request-1" not in metrics
    assert "abc123" not in metrics


def test_contract_rejects_request_id_as_metric_label() -> None:
    original = load_telemetry_contract(Path("configs/observability/telemetry.yaml"))
    labels = original.labels.__class__(
        resource=original.labels.resource,
        request_metrics=(*original.labels.request_metrics, "request_id"),
        prediction_metrics=original.labels.prediction_metrics,
        logs_and_traces=original.labels.logs_and_traces,
    )
    with pytest.raises(ValueError, match="request_id"):
        TelemetryContract(
            schema_version=original.schema_version,
            service_name=original.service_name,
            service_namespace=original.service_namespace,
            environment=original.environment,
            labels=labels,
            metrics=original.metrics,
        )
