"""KServe V2 custom predictor backed by the approved sklearn bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import uvicorn
from aiqa_core.adapters.config import load_feature_contract
from aiqa_serving.adapters import LocalSklearnRiskScorer
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class KServeModelSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIQA_KSERVE_",
        secrets_dir="/var/run/secrets/aiqa/kserve-model",
        extra="forbid",
    )

    model_name: str = "mortality-risk"
    port: int = 8080
    model_bundle_path: Path
    feature_contract_path: Path


class InferInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    shape: list[int]
    datatype: str
    data: list[Any]


class InferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    inputs: list[InferInput]


def build_kserve_model_app(settings: KServeModelSettings) -> FastAPI:
    feature_set = load_feature_contract(settings.feature_contract_path)
    scorer = LocalSklearnRiskScorer(
        settings.model_bundle_path,
        _sha256(settings.feature_contract_path),
    )
    app = FastAPI(title="AIQA KServe mortality-risk predictor")

    @app.get("/v2/health/live")
    def live() -> dict[str, bool]:
        return {"live": True}

    @app.get("/v2/health/ready")
    def ready() -> dict[str, bool]:
        return {"ready": True}

    @app.get("/v2/models/{model_name}/ready")
    def model_ready(model_name: str) -> dict[str, bool]:
        _require_model(model_name, settings.model_name)
        return {"ready": True}

    @app.post("/v2/models/{model_name}/infer")
    def infer(model_name: str, request: InferRequest) -> dict[str, object]:
        _require_model(model_name, settings.model_name)
        if len(request.inputs) != 1:
            raise _invalid("exactly one input tensor is required")
        tensor = request.inputs[0]
        if tensor.name != "features" or tensor.datatype != "BYTES":
            raise _invalid("input tensor must be named features with BYTES datatype")
        if tensor.shape != [1] or len(tensor.data) != 1:
            raise _invalid("input tensor shape must be [1]")
        try:
            features: Any = json.loads(tensor.data[0])
        except (TypeError, json.JSONDecodeError) as error:
            raise _invalid("features tensor must contain one JSON object") from error
        if not isinstance(features, dict):
            raise _invalid("features tensor must contain one JSON object")
        if tuple(features) != feature_set.feature_names:
            raise _invalid("feature names or order do not match the model contract")
        score = scorer.score(tuple(features.items()))
        return {
            "model_name": settings.model_name,
            "model_version": scorer.identity.version,
            "id": request.id,
            "outputs": [
                {
                    "name": "risk_score",
                    "shape": [1, 1],
                    "datatype": "FP64",
                    "data": [[score]],
                }
            ],
        }

    return app


def create_runtime_app() -> FastAPI:
    return build_kserve_model_app(KServeModelSettings())


def main() -> None:
    settings = KServeModelSettings()
    uvicorn.run(build_kserve_model_app(settings), host="0.0.0.0", port=settings.port)


def _require_model(actual: str, expected: str) -> None:
    if actual != expected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="unknown model"
        )


def _invalid(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "INVALID_INFERENCE_REQUEST", "message": message},
    )


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
