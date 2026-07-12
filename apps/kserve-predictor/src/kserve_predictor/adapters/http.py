"""FastAPI route registration for the KServe V2 delivery contract."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from aiqa_observability import Telemetry
from aiqa_observability.adapters import telemetry_lifespan
from aiqa_serving.domain import PredictionRequest, ScoredRisk
from aiqa_serving.ports import RiskScorer
from fastapi import FastAPI, Request

from kserve_predictor.adapters.kserve_v2 import (
    KSERVE_SCENARIO,
    REQUEST_ID_HEADER,
    InferRequestDto,
    InferResponseDto,
    LivenessResponseDto,
    ReadinessResponseDto,
    ensure_scorer_ready,
    invalid_inference_request,
    parse_inference_request,
    render_inference_response,
    validate_requested_model,
)

KSERVE_HTTP_OPERATION = "kserve.http.request"
KSERVE_HTTP_COMPLETED_EVENT = "kserve.http.completed"
KSERVE_INFERENCE_OPERATION = "kserve.infer"
KSERVE_INFERENCE_COMPLETED_EVENT = "kserve.inference.completed"


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
        """Bind request context and emit one completion event for every response."""
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        with telemetry.request_scope(
            request_id=request_id,
            scenario=KSERVE_SCENARIO,
            operation=KSERVE_HTTP_OPERATION,
        ):
            try:
                response = await call_next(request)
                status_code = response.status_code
                response.headers[REQUEST_ID_HEADER] = request_id
                return response
            finally:
                telemetry.event(
                    KSERVE_HTTP_COMPLETED_EVENT,
                    attributes={
                        "duration_seconds": round(time.perf_counter() - started, 6),
                        "method": request.method,
                        "status_code": status_code,
                    },
                )

    @app.get("/v2/health/live", response_model=LivenessResponseDto)
    def live() -> LivenessResponseDto:
        """Report that the predictor process can answer HTTP requests."""
        return LivenessResponseDto(live=True)

    @app.get("/v2/health/ready", response_model=ReadinessResponseDto)
    def ready() -> ReadinessResponseDto:
        """Report whether the configured model scorer is ready to serve."""
        ensure_scorer_ready(scorer)
        return ReadinessResponseDto(ready=True)

    @app.get(
        "/v2/models/{requested_model_name}/ready",
        response_model=ReadinessResponseDto,
    )
    def model_ready(requested_model_name: str) -> ReadinessResponseDto:
        """Report readiness only for this process's declared model name."""
        validate_requested_model(requested_model_name, model_name)
        ensure_scorer_ready(scorer)
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
        """Translate and score one KServe V2 tensor through the bound operation."""
        with telemetry.operation_scope(
            KSERVE_INFERENCE_OPERATION,
            attributes={"model_name": requested_model_name},
        ):
            validate_requested_model(requested_model_name, model_name)
            scoring_request = parse_inference_request(
                body,
                request_id=request.state.request_id,
            )
            try:
                scored = score_operation(scoring_request)
            except ValueError as error:
                raise invalid_inference_request(str(error)) from error
            telemetry.event(
                KSERVE_INFERENCE_COMPLETED_EVENT,
                attributes={
                    "model_name": model_name,
                    "model_version": scored.model.version,
                    "score": scored.score,
                },
            )
            return render_inference_response(
                model_name=model_name,
                inference_id=body.id,
                scored=scored,
            )

    return app
