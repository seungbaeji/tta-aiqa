"""FastAPI inbound adapter for mortality-risk predictions."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from aiqa_observability import is_valid_correlation_id
from aiqa_observability.adapters import telemetry_lifespan
from aiqa_serving.domain import PredictionRequest, RiskPrediction
from aiqa_serving.ports import RiskScorer
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from risk_api.adapters.config import ApiConfig
from risk_api.adapters.telemetry import RiskApiTelemetry

MODEL_BACKEND_NOT_READY_CODE = "MODEL_BACKEND_NOT_READY"
MODEL_INPUT_INVALID_CODE = "MODEL_INPUT_INVALID"
REQUEST_BODY_TOO_LARGE_CODE = "REQUEST_BODY_TOO_LARGE"
UNSPECIFIED_SCENARIO = "unspecified"
PREDICTION_ROUTE = "/v1/predict"
RISK_API_TRACE_EXCLUDED_URLS = (
    r"/health/(?:live|ready)(?:\?.*)?$," r"/metrics(?:\?.*)?$"
)


def normalize_external_correlation_id(
    value: str | None,
    *,
    fallback: str | None,
) -> str | None:
    """Accept only bounded correlation values; never treat them as identity."""
    if not is_valid_correlation_id(value):
        return fallback
    return value


async def request_body_exceeds_limit(request: Request, limit: int) -> bool:
    """Read and cache at most one bounded request body for downstream parsing."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > limit:
                return True
        except ValueError:
            pass

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            return True
        body.extend(chunk)
    request._body = bytes(body)  # noqa: SLF001 - Starlette middleware replay contract
    return False


def validation_category(error: ValueError) -> str:
    """Map an internal validation message to one bounded operational category."""
    message = str(error).lower()
    if "missing=[" in message and "missing=[]" not in message:
        return "missing"
    if "extra=[" in message and "extra=[]" not in message:
        return "extra"
    if any(
        marker in message
        for marker in ("invalid type", "is not finite", "non-nullable feature is null")
    ):
        return "type"
    return "other"


def request_validation_category(error: RequestValidationError) -> str:
    """Classify framework validation without serializing request-controlled input."""
    error_types = {
        str(item.get("type", ""))
        for item in error.errors()
        if isinstance(item, dict)
    }
    if any(item == "missing" or item.endswith("_missing") for item in error_types):
        return "missing"
    if "extra_forbidden" in error_types:
        return "extra"
    if any(
        item == "json_invalid"
        or item == "finite_number"
        or item.endswith("_type")
        or item.endswith("_parsing")
        for item in error_types
    ):
        return "type"
    return "other"


def model_input_invalid_detail(validation_category: str) -> dict[str, str]:
    """Return the one bounded public response shared by all validation paths."""
    return {
        "code": MODEL_INPUT_INVALID_CODE,
        "validation_category": validation_category,
        "message": "model input does not match the public contract",
    }


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
    education_only: bool


def build_http_app(
    *,
    config: ApiConfig,
    feature_count: int,
    predict_operation: Callable[[PredictionRequest], RiskPrediction],
    scorer: RiskScorer,
    backend: str,
    telemetry: RiskApiTelemetry,
) -> FastAPI:
    """Build the REST delivery adapter around bound serving operations."""
    app = FastAPI(
        title=config.title,
        version=config.api_version,
        lifespan=telemetry_lifespan(telemetry.shutdown),
    )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        """Convert DTO failures into bounded response and telemetry contracts."""
        input_error_category = request_validation_category(error)
        with telemetry.prediction_scope():
            telemetry.record_input_validation_failure(
                error_code=MODEL_INPUT_INVALID_CODE,
                validation_category=input_error_category,
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": model_input_invalid_detail(input_error_category)},
        )

    @app.middleware("http")
    async def observe_http(request: Request, call_next):
        """Bind context and record business signals for prediction responses."""
        request_id = normalize_external_correlation_id(
            request.headers.get(config.request_id_header),
            fallback=str(uuid.uuid4()),
        )
        assert request_id is not None
        run_id = normalize_external_correlation_id(
            request.headers.get(config.run_id_header),
            fallback=None,
        )
        scenario = request.headers.get(config.scenario_header, UNSPECIFIED_SCENARIO)
        with telemetry.request_scope(
            request_id=request_id,
            run_id=run_id,
            scenario=scenario,
        ) as normalized:
            request.state.request_id = request_id
            request.state.scenario = normalized
            started = time.perf_counter()
            status_code = 500
            try:
                if (
                    request.method == "POST"
                    and request.url.path == PREDICTION_ROUTE
                    and await request_body_exceeds_limit(
                        request,
                        config.max_request_body_bytes,
                    )
                ):
                    status_code = status.HTTP_413_CONTENT_TOO_LARGE
                    telemetry.record_request_rejection(
                        error_code=REQUEST_BODY_TOO_LARGE_CODE,
                        rejection_category="body_too_large",
                    )
                    response = JSONResponse(
                        status_code=status_code,
                        content={
                            "detail": {
                                "code": REQUEST_BODY_TOO_LARGE_CODE,
                                "message": "request body exceeds the configured limit",
                            }
                        },
                    )
                else:
                    response = await call_next(request)
                status_code = response.status_code
                response.headers[config.request_id_header] = request_id
                return response
            finally:
                matched_route = getattr(request.scope.get("route"), "path", None)
                if matched_route is None and request.url.path == PREDICTION_ROUTE:
                    matched_route = PREDICTION_ROUTE
                route = telemetry.normalize_route(matched_route)
                if route == PREDICTION_ROUTE:
                    telemetry.observe_request(
                        route=route,
                        method=request.method,
                        status_code=status_code,
                        duration_seconds=time.perf_counter() - started,
                        scenario=request.state.scenario,
                    )

    @app.get("/health/live")
    def live() -> dict[str, str]:
        """Report that the public API process can handle HTTP requests."""
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        """Report readiness only when the configured scoring backend is available."""
        if not scorer.ready():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": MODEL_BACKEND_NOT_READY_CODE},
            )
        return {"status": "ready", "model_version": scorer.identity.version}

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> PlainTextResponse:
        """Expose the bounded application metrics for Alloy scraping."""
        return PlainTextResponse(
            telemetry.render_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.get("/v1/model")
    def model_info() -> dict[str, object]:
        """Return non-secret identity metadata for the current scoring backend."""
        return {
            "backend": backend,
            "profile": scorer.identity.profile,
            "version": scorer.identity.version,
            "threshold": scorer.identity.threshold,
            "feature_count": feature_count,
            "education_only": config.education_only,
        }

    @app.post(PREDICTION_ROUTE, response_model=PredictionResponse)
    def predict(
        body: PredictionBody,
        response: Response,
        request: Request,
    ) -> PredictionResponse:
        """Translate, validate, and score one public mortality-risk request."""
        resolved_request_id = request.state.request_id
        response.headers[config.request_id_header] = resolved_request_id
        input_error_category: str | None = None
        with telemetry.prediction_scope():
            try:
                result = predict_operation(
                    PredictionRequest(
                        request_id=resolved_request_id,
                        features=tuple(body.features.items()),
                        scenario=request.state.scenario,
                    )
                )
            except ValueError as error:
                input_error_category = validation_category(error)
                telemetry.record_input_validation_failure(
                    error_code=MODEL_INPUT_INVALID_CODE,
                    validation_category=input_error_category,
                )
        if input_error_category is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=model_input_invalid_detail(input_error_category),
            )
        return PredictionResponse(
            request_id=result.request_id,
            model_profile=result.model.profile,
            model_version=result.model.version,
            score=round(result.score, config.score_decimal_places),
            threshold=result.model.threshold,
            prediction=result.label,
            education_only=config.education_only,
        )

    return app
