"""KServe V2 predictor contract tests."""

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi.testclient import TestClient
from kserve_predictor.bootstrap import build_application
from kserve_predictor.settings import KServePredictorSettings
from sklearn.linear_model import LogisticRegression


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    contract = tmp_path / "contract.yaml"
    contract.write_text(
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
    model = LogisticRegression().fit(
        pd.DataFrame({"age": [20.0, 30.0, 70.0, 80.0], "age__missing": [0, 0, 0, 0]}),
        [0, 0, 1, 1],
    )
    bundle = tmp_path / "model.joblib"
    joblib.dump(
        {
            "model": model,
            "metadata": {
                "profile": "candidate-b",
                "threshold": 0.35,
                "feature_contract": {
                    "sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
                    "features": [{"name": "age"}, {"name": "age__missing"}],
                },
            },
        },
        bundle,
    )
    return contract, bundle


def test_custom_predictor_implements_kserve_v2_probability_contract(
    tmp_path: Path,
) -> None:
    contract, bundle = _write_fixture(tmp_path)
    app = build_application(
        KServePredictorSettings(
            _secrets_dir=tmp_path,
            model_name="mortality-risk",
            model_bundle_path=bundle,
            feature_contract_path=contract,
        )
    )

    response = TestClient(app).post(
        "/v2/models/mortality-risk/infer",
        json={
            "id": "request-1",
            "inputs": [
                {
                    "name": "features",
                    "shape": [1],
                    "datatype": "BYTES",
                    "data": ['{"age":68.0,"age__missing":false}'],
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "request-1"
    assert body["outputs"][0]["name"] == "risk_score"
    assert 0 <= body["outputs"][0]["data"][0][0] <= 1


def test_custom_predictor_rejects_wrong_tensor_shape(tmp_path: Path) -> None:
    contract, bundle = _write_fixture(tmp_path)
    client = TestClient(
        build_application(
            KServePredictorSettings(
                _secrets_dir=tmp_path,
                model_bundle_path=bundle,
                feature_contract_path=contract,
            )
        )
    )

    response = client.post(
        "/v2/models/mortality-risk/infer",
        json={
            "inputs": [
                {"name": "features", "shape": [2], "datatype": "BYTES", "data": ["{}"]}
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_INFERENCE_REQUEST"


def test_custom_predictor_uses_shared_input_validation(tmp_path: Path) -> None:
    contract, bundle = _write_fixture(tmp_path)
    client = TestClient(
        build_application(
            KServePredictorSettings(
                _secrets_dir=tmp_path,
                model_bundle_path=bundle,
                feature_contract_path=contract,
            )
        )
    )

    reordered = client.post(
        "/v2/models/mortality-risk/infer",
        json={
            "inputs": [
                {
                    "name": "features",
                    "shape": [1],
                    "datatype": "BYTES",
                    "data": ['{"age__missing":false,"age":68.0}'],
                }
            ]
        },
    )
    invalid = client.post(
        "/v2/models/mortality-risk/infer",
        json={
            "inputs": [
                {
                    "name": "features",
                    "shape": [1],
                    "datatype": "BYTES",
                    "data": ['{"age":68.0,"age__missing":"false"}'],
                }
            ]
        },
    )

    assert reordered.status_code == 200
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "INVALID_INFERENCE_REQUEST"


def test_custom_predictor_readiness_reflects_loaded_backend(tmp_path: Path) -> None:
    contract, bundle = _write_fixture(tmp_path)
    client = TestClient(
        build_application(
            KServePredictorSettings(
                _secrets_dir=tmp_path,
                model_bundle_path=bundle,
                feature_contract_path=contract,
            )
        )
    )

    assert client.get("/v2/health/ready").json() == {"ready": True}
    assert client.get("/v2/models/mortality-risk/ready").json() == {"ready": True}


def test_custom_predictor_preserves_inbound_trace_and_request_id(
    tmp_path: Path, capsys
) -> None:
    contract, bundle = _write_fixture(tmp_path)
    app = build_application(
        KServePredictorSettings(
            _secrets_dir=tmp_path,
            model_bundle_path=bundle,
            feature_contract_path=contract,
        )
    )
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    headers = {
        "traceparent": f"00-{trace_id}-00f067aa0ba902b7-01",
        "X-Request-ID": "risk-api-request-123",
    }

    with TestClient(app) as client:
        response = client.get("/v2/health/live", headers=headers)

    events = [
        json.loads(line)
        for line in capsys.readouterr().err.splitlines()
        if '"event":"kserve.http.completed"' in line
    ]
    assert response.headers["X-Request-ID"] == "risk-api-request-123"
    assert events[-1]["trace_id"] == trace_id
    assert events[-1]["request_id"] == "risk-api-request-123"
