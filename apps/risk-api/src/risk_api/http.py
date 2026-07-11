"""FastAPI inbound adapter for mortality-risk predictions."""

from __future__ import annotations

import math
import uuid
from typing import Any

from aiqa_core.domain import FeatureSet, FeatureType
from aiqa_observability.adapters import TelemetryRuntime
from aiqa_serving.adapters import LocalSklearnRiskScorer
from aiqa_serving.application import PredictRisk
from aiqa_serving.domain import FeatureValue, PredictionRequest
from aiqa_serving.ports import RiskScorer
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field

from risk_api.config import ApiConfig
from risk_api.telemetry import current_trace_id


class PredictionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: dict[str, Any] = Field(min_length=1)


class PredictionResponse(BaseModel):
    request_id: str
    model_profile: str
    model_version: str
    score: float
    threshold: float
    prediction: str


def build_http_app(
    *,
    config: ApiConfig,
    feature_set: FeatureSet,
    predict_risk: PredictRisk,
    scorer: RiskScorer,
    backend: str,
    telemetry: TelemetryRuntime,
) -> FastAPI:
    app = FastAPI(title=config.title, version=config.api_version)

    @app.middleware("http")
    async def observe_http(request: Request, call_next):
        request_id = request.headers.get(config.request_id_header) or str(uuid.uuid4())
        scenario = request.headers.get(config.scenario_header, "unspecified")
        request.state.request_id = request_id
        span = trace.get_current_span()
        span.set_attribute("aiqa.request_id", request_id)
        span.set_attribute("aiqa.scenario", scenario)
        started = telemetry.clock()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[config.request_id_header] = request_id
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", request.url.path)
            telemetry.observe_request(
                request_id=request_id,
                route=route,
                method=request.method,
                status_code=status_code,
                duration_seconds=telemetry.clock() - started,
                scenario=scenario,
                trace_id=current_trace_id(),
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
            "feature_count": len(feature_set.features),
            "education_only": config.education_only,
        }

    @app.post("/v1/predict", response_model=PredictionResponse)
    def predict(
        body: PredictionBody,
        response: Response,
        request: Request,
        request_id: str | None = Header(default=None, alias=config.request_id_header),
        scenario: str = Header(default="unspecified", alias=config.scenario_header),
    ) -> PredictionResponse:
        resolved_request_id = request_id or request.state.request_id
        response.headers[config.request_id_header] = resolved_request_id
        try:
            values = validate_feature_values(body.features, feature_set)
            result = predict_risk.execute(
                PredictionRequest(
                    request_id=resolved_request_id,
                    features=values,
                    scenario=scenario,
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
            prediction=(
                config.positive_label if result.positive else config.negative_label
            ),
        )

    @app.post("/v1/model/reload")
    def reload_model() -> dict[str, object]:
        if not isinstance(scorer, LocalSklearnRiskScorer):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "RELOAD_UNSUPPORTED", "backend": backend},
            )
        identity = scorer.reload()
        return {"reloaded": True, "model_version": identity.version}

    return app


def validate_feature_values(
    payload: dict[str, Any], feature_set: FeatureSet
) -> tuple[tuple[str, FeatureValue], ...]:
    expected = set(feature_set.feature_names)
    actual = set(payload)
    if actual != expected:
        raise ValueError(
            f"model input contract mismatch: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    values: list[tuple[str, FeatureValue]] = []
    for feature in feature_set.features:
        value = payload[feature.name]
        if value is None:
            if not feature.nullable:
                raise ValueError(f"non-nullable feature is null: {feature.name}")
        elif feature.dtype is FeatureType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValueError(f"boolean feature has invalid type: {feature.name}")
        elif feature.dtype in {FeatureType.FLOAT, FeatureType.INTEGER}:
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError(f"numeric feature has invalid type: {feature.name}")
            if not math.isfinite(float(value)):
                raise ValueError(f"numeric feature is not finite: {feature.name}")
        elif feature.dtype is FeatureType.CATEGORY and not isinstance(
            value, str | int | float
        ):
            raise ValueError(f"category feature has invalid type: {feature.name}")
        values.append((feature.name, value))
    return tuple(values)
