"""Run serving contract smoke checks against the in-process FastAPI app."""

from __future__ import annotations

import os
from typing import Any

from ai_quality.labs.ch03_serving import (
    build_test_client,
    load_serving_payload,
    load_yaml_config,
)
from ai_quality.serving.domain.skew_check import verify_feature_compatibility


def _schema_names(openapi: dict[str, Any]) -> list[str]:
    return sorted(openapi["components"]["schemas"])


def main() -> None:
    """Check schema exposure, valid prediction, invalid request, and skew."""
    os.environ.setdefault(
        "EVENT_LOG_PATH",
        "outputs/check_serving_contract_prediction_events.jsonl",
    )
    client = build_test_client()

    openapi = client.get("/openapi.json").json()
    valid_response = client.post("/predict", json=load_serving_payload())
    invalid_response = client.post(
        "/predict",
        json={
            "request_id": "lab-03-invalid-001",
            "heart_rate": "not-a-number",
        },
    )

    model_features = load_yaml_config("validation", "model_features.yaml")
    model_thresholds = load_yaml_config("validation", "model_thresholds.yaml")
    model_metadata = load_yaml_config("validation", "model_metadata.yaml")
    serving = load_yaml_config("operations", "serving.yaml")
    skew_result = verify_feature_compatibility(
        training_features=list(model_features["feature_columns"]),
        serving_features=list(model_metadata["feature_columns"]),
        training_threshold=float(model_thresholds["operating_threshold"]),
        serving_threshold=float(serving["threshold"]),
    )

    checks = {
        "openapi_has_prediction_payload": "PredictionPayload"
        in _schema_names(openapi),
        "valid_prediction_status": valid_response.status_code == 200,
        "invalid_payload_rejected": invalid_response.status_code == 422,
        "train_serving_contract": skew_result.passed,
    }

    for name, passed in checks.items():
        print(f"{name}={passed}")

    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
