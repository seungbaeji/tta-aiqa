"""Risk API adapter behavior independent from FastAPI and model runtimes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aiqa_observability import TelemetryResource
from aiqa_serving.domain import PredictionEvent
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
