"""FastAPI inbound adapter for mortality-risk predictions."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from aiqa_observability.adapters import telemetry_lifespan
from aiqa_serving.domain import ModelIdentity, PredictionRequest, RiskPrediction
from aiqa_serving.ports import RiskScorer
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from risk_api.config import ApiConfig
from risk_api.telemetry import RiskApiTelemetry


class PredictionBody(BaseModel):
    """External REST request body for a mortality-risk prediction."""

    model_config = ConfigDict(extra="forbid")

    features: dict[str, Any] = Field(min_length=1)


class PredictionResponse(BaseModel):
    """External REST response body for a mortality-risk prediction."""

    request_id: str
    model_profile: str
    model_version: str
    score: float
    threshold: float
    prediction: str


def build_http_app(
    *,
    config: ApiConfig,
    feature_count: int,
    predict_operation: Callable[[PredictionRequest], RiskPrediction],
    scorer: RiskScorer,
    backend: str,
    reload_operation: Callable[[], ModelIdentity] | None,
    telemetry: RiskApiTelemetry,
) -> FastAPI:
    """Build the REST delivery adapter around bound serving operations."""
    app = FastAPI(
        title=config.title,
        version=config.api_version,
        lifespan=telemetry_lifespan(telemetry.shutdown),
    )

    @app.middleware("http")
    async def observe_http(request: Request, call_next):
        request_id = request.headers.get(config.request_id_header) or str(uuid.uuid4())
        scenario = request.headers.get(config.scenario_header, "unspecified")
        with telemetry.request_scope(
            request_id=request_id, scenario=scenario
        ) as normalized:
            request.state.request_id = request_id
            request.state.scenario = normalized
            started = telemetry.clock()
            status_code = 500
            try:
                response = await call_next(request)
                status_code = response.status_code
                response.headers[config.request_id_header] = request_id
                return response
            finally:
                matched_route = getattr(request.scope.get("route"), "path", None)
                telemetry.observe_request(
                    route=telemetry.normalize_route(matched_route),
                    method=request.method,
                    status_code=status_code,
                    duration_seconds=telemetry.clock() - started,
                )

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        if not scorer.ready():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "MODEL_BACKEND_NOT_READY"},
            )
        return {"status": "ready", "model_version": scorer.identity.version}

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> PlainTextResponse:
        return PlainTextResponse(
            telemetry.render_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.get("/v1/model")
    def model_info() -> dict[str, object]:
        return {
            "backend": backend,
            "profile": scorer.identity.profile,
            "version": scorer.identity.version,
            "threshold": scorer.identity.threshold,
            "feature_count": feature_count,
            "education_only": config.education_only,
        }

    @app.post("/v1/predict", response_model=PredictionResponse)
    def predict(
        body: PredictionBody,
        response: Response,
        request: Request,
    ) -> PredictionResponse:
        resolved_request_id = request.state.request_id
        response.headers[config.request_id_header] = resolved_request_id
        try:
            with telemetry.prediction_scope():
                result = predict_operation(
                    PredictionRequest(
                        request_id=resolved_request_id,
                        features=tuple(body.features.items()),
                        scenario=request.state.scenario,
                    )
                )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "MODEL_INPUT_INVALID", "message": str(error)},
            ) from error
        return PredictionResponse(
            request_id=result.request_id,
            model_profile=result.model.profile,
            model_version=result.model.version,
            score=round(result.score, config.score_decimal_places),
            threshold=result.model.threshold,
            prediction=result.label,
        )

    @app.post("/v1/model/reload")
    def reload_model() -> dict[str, object]:
        if reload_operation is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "RELOAD_UNSUPPORTED", "backend": backend},
            )
        identity = reload_operation()
        return {"reloaded": True, "model_version": identity.version}

    return app
