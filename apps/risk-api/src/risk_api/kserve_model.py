"""KServe V2 custom predictor backed by the approved sklearn bundle."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import create_telemetry, load_telemetry_policy
from aiqa_observability.adapters import instrument_fastapi, telemetry_lifespan
from aiqa_serving.adapters import LocalSklearnRiskScorer
from aiqa_serving.application import validate_feature_values
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import AnyHttpUrl, BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

REQUEST_ID_HEADER = "X-Request-ID"


class KServeModelSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIQA_KSERVE_",
        secrets_dir="/var/run/secrets/aiqa/kserve-model",
        extra="forbid",
    )

    model_name: str = "mortality-risk"
    port: int = 8080
    environment: str = "local"
    telemetry_config_path: Path = Path("configs/observability/telemetry.yaml")
    otlp_endpoint: AnyHttpUrl | None = None
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
    telemetry = create_telemetry(
        service_name="kserve-risk-predictor",
        environment=settings.environment,
        policy=load_telemetry_policy(settings.telemetry_config_path),
        otlp_endpoint=str(settings.otlp_endpoint) if settings.otlp_endpoint else None,
    )
    app = FastAPI(
        title="AIQA KServe mortality-risk predictor",
        lifespan=telemetry_lifespan(telemetry.shutdown),
    )

    @app.middleware("http")
    async def observe_http(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        started = time.perf_counter()
        status_code = 500
        with telemetry.request_scope(
            request_id=request_id,
            scenario="kserve",
            operation="kserve.http.request",
        ):
            try:
                response = await call_next(request)
                status_code = response.status_code
                response.headers[REQUEST_ID_HEADER] = request_id
                return response
            finally:
                telemetry.event(
                    "kserve.http.completed",
                    attributes={
                        "duration_seconds": round(time.perf_counter() - started, 6),
                        "method": request.method,
                        "status_code": status_code,
                    },
                )

    @app.get("/v2/health/live")
    def live() -> dict[str, bool]:
        return {"live": True}

    @app.get("/v2/health/ready")
    def ready() -> dict[str, bool]:
        if not scorer.ready():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "MODEL_BACKEND_NOT_READY"},
            )
        return {"ready": True}

    @app.get("/v2/models/{model_name}/ready")
    def model_ready(model_name: str) -> dict[str, bool]:
        _require_model(model_name, settings.model_name)
        if not scorer.ready():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "MODEL_BACKEND_NOT_READY"},
            )
        return {"ready": True}

    @app.post("/v2/models/{model_name}/infer")
    def infer(model_name: str, request: InferRequest) -> dict[str, object]:
        with telemetry.operation_scope(
            "kserve.infer", attributes={"model_name": model_name}
        ):
            _require_model(model_name, settings.model_name)
            if len(request.inputs) != 1:
                raise _invalid("exactly one input tensor is required")
            tensor = request.inputs[0]
            if tensor.name != "features" or tensor.datatype != "BYTES":
                raise _invalid(
                    "input tensor must be named features with BYTES datatype"
                )
            if tensor.shape != [1] or len(tensor.data) != 1:
                raise _invalid("input tensor shape must be [1]")
            try:
                features: Any = json.loads(tensor.data[0])
            except (TypeError, json.JSONDecodeError) as error:
                raise _invalid(
                    "features tensor must contain one JSON object"
                ) from error
            if not isinstance(features, dict):
                raise _invalid("features tensor must contain one JSON object")
            try:
                values = validate_feature_values(features, feature_set)
            except ValueError as error:
                raise _invalid(str(error)) from error
            score = scorer.score(values)
            telemetry.event(
                "kserve.inference.completed",
                attributes={
                    "model_name": settings.model_name,
                    "model_version": scorer.identity.version,
                    "score": score,
                },
            )
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

    instrument_fastapi(app, telemetry.tracing)
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
