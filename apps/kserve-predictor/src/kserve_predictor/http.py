"""KServe V2 FastAPI delivery adapter."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from aiqa_observability import Telemetry
from aiqa_observability.adapters import telemetry_lifespan
from aiqa_serving.domain import PredictionRequest, ScoredRisk
from aiqa_serving.ports import RiskScorer
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

REQUEST_ID_HEADER = "X-Request-ID"
_FEATURES_DOCUMENT = TypeAdapter(dict[str, Any])


class InferInputDto(BaseModel):
    """External KServe V2 input tensor DTO."""

    model_config = ConfigDict(extra="forbid")

    name: str
    shape: list[int]
    datatype: str
    data: list[Any]


class InferRequestDto(BaseModel):
    """External KServe V2 inference request DTO."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    inputs: list[InferInputDto]


class InferOutputDto(BaseModel):
    """External KServe V2 output tensor DTO."""

    name: str
    shape: list[int]
    datatype: str
    data: list[list[float]]


class InferResponseDto(BaseModel):
    """External KServe V2 inference response DTO."""

    model_name: str
    model_version: str
    id: str | None
    outputs: list[InferOutputDto]


class LivenessResponseDto(BaseModel):
    """External KServe liveness response DTO."""

    live: bool


class ReadinessResponseDto(BaseModel):
    """External KServe readiness response DTO."""

    ready: bool


def build_http_app(
    *,
    model_name: str,
    score_operation: Callable[[PredictionRequest], ScoredRisk],
    scorer: RiskScorer,
    telemetry: Telemetry,
) -> FastAPI:
    """Build the KServe V2 delivery adapter around a bound score operation."""
    app = FastAPI(
        title="AIQA KServe mortality-risk predictor",
        lifespan=telemetry_lifespan(telemetry.shutdown),
    )

    @app.middleware("http")
    async def observe_http(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
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

    @app.get("/v2/health/live", response_model=LivenessResponseDto)
    def live() -> LivenessResponseDto:
        return LivenessResponseDto(live=True)

    @app.get("/v2/health/ready", response_model=ReadinessResponseDto)
    def ready() -> ReadinessResponseDto:
        _require_ready(scorer)
        return ReadinessResponseDto(ready=True)

    @app.get(
        "/v2/models/{requested_model_name}/ready",
        response_model=ReadinessResponseDto,
    )
    def model_ready(requested_model_name: str) -> ReadinessResponseDto:
        _require_model(requested_model_name, model_name)
        _require_ready(scorer)
        return ReadinessResponseDto(ready=True)

    @app.post(
        "/v2/models/{requested_model_name}/infer",
        response_model=InferResponseDto,
    )
    def infer(
        requested_model_name: str,
        body: InferRequestDto,
        request: Request,
    ) -> InferResponseDto:
        with telemetry.operation_scope(
            "kserve.infer", attributes={"model_name": requested_model_name}
        ):
            _require_model(requested_model_name, model_name)
            features = _features(body)
            try:
                scored = score_operation(
                    PredictionRequest(
                        request_id=request.state.request_id,
                        features=tuple(features.items()),
                        scenario="kserve",
                    )
                )
            except ValueError as error:
                raise _invalid(str(error)) from error
            telemetry.event(
                "kserve.inference.completed",
                attributes={
                    "model_name": model_name,
                    "model_version": scored.model.version,
                    "score": scored.score,
                },
            )
            return InferResponseDto(
                model_name=model_name,
                model_version=scored.model.version,
                id=body.id,
                outputs=[
                    InferOutputDto(
                        name="risk_score",
                        shape=[1, 1],
                        datatype="FP64",
                        data=[[scored.score]],
                    )
                ],
            )

    return app


def _features(body: InferRequestDto) -> dict[str, Any]:
    if len(body.inputs) != 1:
        raise _invalid("exactly one input tensor is required")
    tensor = body.inputs[0]
    if tensor.name != "features" or tensor.datatype != "BYTES":
        raise _invalid("input tensor must be named features with BYTES datatype")
    if tensor.shape != [1] or len(tensor.data) != 1:
        raise _invalid("input tensor shape must be [1]")
    try:
        return _FEATURES_DOCUMENT.validate_json(tensor.data[0])
    except (TypeError, ValidationError, ValueError) as error:
        raise _invalid("features tensor must contain one JSON object") from error


def _require_model(actual: str, expected: str) -> None:
    if actual != expected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="unknown model"
        )


def _require_ready(scorer: RiskScorer) -> None:
    if not scorer.ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_BACKEND_NOT_READY"},
        )


def _invalid(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "INVALID_INFERENCE_REQUEST", "message": message},
    )
