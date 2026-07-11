"""Local sklearn and KServe scoring adapter tests."""

from pathlib import Path

import httpx
import joblib
import pandas as pd
import pytest
from aiqa_serving.adapters import KServeRiskScorer, LocalSklearnRiskScorer
from aiqa_serving.domain import ModelIdentity
from sklearn.linear_model import LogisticRegression


def write_bundle(path: Path, contract_hash: str = "contract-hash") -> None:
    model = LogisticRegression().fit(
        pd.DataFrame({"age": [20.0, 30.0, 70.0, 80.0]}), [0, 0, 1, 1]
    )
    joblib.dump(
        {
            "model": model,
            "metadata": {
                "profile": "candidate-b",
                "threshold": 0.35,
                "feature_contract": {
                    "sha256": contract_hash,
                    "features": [{"name": "age", "dtype": "float", "nullable": False}],
                },
            },
        },
        path,
    )


def test_local_sklearn_adapter_validates_contract_and_scores(tmp_path: Path) -> None:
    path = tmp_path / "model.joblib"
    write_bundle(path)

    scorer = LocalSklearnRiskScorer(path, "contract-hash")

    assert scorer.identity.profile == "candidate-b"
    assert scorer.identity.version.startswith("candidate-b-")
    assert scorer.identity.threshold == pytest.approx(0.35)
    assert scorer.ready() is True
    assert 0 <= scorer.score((("age", 65.0),)) <= 1


def test_local_sklearn_adapter_rejects_contract_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "model.joblib"
    write_bundle(path)

    with pytest.raises(ValueError, match="contract hash mismatch"):
        LocalSklearnRiskScorer(path, "different-hash")


def test_kserve_adapter_uses_v2_protocol_and_positive_probability() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert request.url.path == "/v2/models/mortality-risk/ready"
            return httpx.Response(200, json={"ready": True})
        assert request.url.path == "/v2/models/mortality-risk/infer"
        document = __import__("json").loads(request.content)
        assert document["inputs"][0]["shape"] == [1]
        assert document["inputs"][0]["datatype"] == "BYTES"
        assert __import__("json").loads(document["inputs"][0]["data"][0]) == {
            "age": 67.0,
            "heart_rate": None,
        }
        return httpx.Response(
            200,
            json={
                "model_name": "mortality-risk",
                "model_version": "v2-abc",
                "outputs": [{"name": "probabilities", "data": [[0.2, 0.8]]}],
            },
        )

    scorer = KServeRiskScorer(
        endpoint="http://kserve.test",
        model_name="mortality-risk",
        feature_names=("age", "heart_rate"),
        identity=ModelIdentity("candidate-b", "v2-abc", 0.35),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert scorer.ready() is True
    assert scorer.score((("age", 67.0), ("heart_rate", None))) == pytest.approx(0.8)


def test_kserve_adapter_rejects_served_model_identity_mismatch() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model_name": "mortality-risk",
                "model_version": "candidate-a-wrong",
                "outputs": [{"name": "risk_score", "data": [[0.8]]}],
            },
        )

    scorer = KServeRiskScorer(
        endpoint="http://kserve.test",
        model_name="mortality-risk",
        feature_names=("age",),
        identity=ModelIdentity("candidate-b", "candidate-b-approved", 0.35),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ValueError, match="model version"):
        scorer.score((("age", 67.0),))
