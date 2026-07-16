"""Risk API local backend integration tests."""

import hashlib
from pathlib import Path

import joblib
import pandas as pd
from fastapi.testclient import TestClient
from risk_api.bootstrap import build_application
from risk_api.settings import RiskApiSettings
from sklearn.linear_model import LogisticRegression


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_contract(path: Path) -> None:
    path.write_text(
        """schema_version: 1
name: test-contract
target: target
features:
  - name: age
    dtype: float
    nullable: true
  - name: age__missing
    dtype: boolean
    nullable: false
""",
        encoding="utf-8",
    )


def write_bundle(path: Path, contract_hash: str) -> None:
    features = pd.DataFrame(
        {
            "age": [20.0, 30.0, 70.0, 80.0],
            "age__missing": [False, False, False, False],
        }
    )
    model = LogisticRegression().fit(features, [0, 0, 1, 1])
    joblib.dump(
        {
            "model": model,
            "metadata": {
                "profile": "baseline",
                "threshold": 0.5,
                "feature_contract": {
                    "name": "test-contract",
                    "sha256": contract_hash,
                    "features": [
                        {"name": "age", "dtype": "float", "nullable": True},
                        {
                            "name": "age__missing",
                            "dtype": "boolean",
                            "nullable": False,
                        },
                    ],
                },
            },
        },
        path,
    )


def client(tmp_path: Path) -> TestClient:
    contract_path = tmp_path / "contract.yaml"
    bundle_path = tmp_path / "model.joblib"
    write_contract(contract_path)
    write_bundle(bundle_path, sha256(contract_path))
    settings = RiskApiSettings(
        _env_file=None,
        _secrets_dir=tmp_path,
        model_backend="local",
        api_config_path="configs/serving/api.yaml",
        feature_contract_path=contract_path,
        telemetry_config_path="configs/observability/telemetry.yaml",
        model_bundle_path=bundle_path,
    )
    return TestClient(build_application(settings))


def test_local_api_predicts_and_exposes_model_identity(tmp_path: Path) -> None:
    api = client(tmp_path)

    response = api.post(
        "/v1/predict",
        headers={"X-Request-ID": "request-123"},
        json={"features": {"age": 68.0, "age__missing": False}},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-123"
    body = response.json()
    assert body["request_id"] == "request-123"
    assert body["model_profile"] == "baseline"
    assert body["model_version"].startswith("baseline-")
    assert body["prediction"] in {"high_risk", "low_risk"}
    model = api.get("/v1/model").json()
    assert model["feature_count"] == 2
    assert model["education_only"] is True


def test_local_api_rejects_contract_errors_without_a_reload_endpoint(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)

    missing = api.post("/v1/predict", json={"features": {"age": 68.0}})
    wrong_type = api.post(
        "/v1/predict",
        json={"features": {"age": 68.0, "age__missing": 0.0}},
    )
    reload_attempt = api.post("/v1/model/reload")

    assert missing.status_code == 422
    assert missing.json()["detail"]["code"] == "MODEL_INPUT_INVALID"
    assert wrong_type.status_code == 422
    assert "boolean feature" in wrong_type.json()["detail"]["message"]
    assert reload_attempt.status_code == 404
    assert 'status_code="422"' in api.get("/metrics").text


def test_api_exposes_prediction_metrics_without_request_id_label(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    api.post(
        "/v1/predict",
        headers={"X-Request-ID": "private-request", "X-AIQA-Scenario": "baseline"},
        json={"features": {"age": 68.0, "age__missing": False}},
    )

    metrics = api.get("/metrics").text

    assert "aiqa_risk_predictions_total" in metrics
    assert 'scenario="baseline"' in metrics
    assert "private-request" not in metrics


def test_api_bounds_unknown_scenarios_and_unmatched_routes(tmp_path: Path) -> None:
    api = client(tmp_path)
    api.post(
        "/v1/predict",
        headers={"X-AIQA-Scenario": "student-unique-scenario-123"},
        json={"features": {"age": 68.0, "age__missing": False}},
    )
    api.get("/missing/first")
    api.get("/missing/second")
    api.request("DELETE", "/health/live")

    metrics = api.get("/metrics").text

    assert 'scenario="other"' in metrics
    assert "student-unique-scenario-123" not in metrics
    assert 'route="unmatched"' in metrics
    assert 'method="other"' in metrics
    assert "/missing/first" not in metrics
    assert "/missing/second" not in metrics
