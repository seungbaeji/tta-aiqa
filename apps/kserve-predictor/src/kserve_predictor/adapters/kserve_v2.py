"""KServe V2 protocol DTOs, translation, and HTTP error contracts."""

from typing import Any

from aiqa_serving.domain import PredictionRequest, ScoredRisk
from aiqa_serving.ports import RiskScorer
from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

REQUEST_ID_HEADER = "X-Request-ID"
KSERVE_SCENARIO = "kserve"
FEATURE_INPUT_NAME = "features"
FEATURE_INPUT_DATATYPE = "BYTES"
RISK_SCORE_OUTPUT_NAME = "risk_score"
RISK_SCORE_OUTPUT_DATATYPE = "FP64"
RISK_SCORE_OUTPUT_SHAPE = (1, 1)
INVALID_INFERENCE_REQUEST_CODE = "INVALID_INFERENCE_REQUEST"
MODEL_BACKEND_NOT_READY_CODE = "MODEL_BACKEND_NOT_READY"
FEATURES_DOCUMENT = TypeAdapter(dict[str, Any])


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


def validate_requested_model(requested_model_name: str, model_name: str) -> None:
    """Reject a KServe route that names a model this process does not own."""
    if requested_model_name != model_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unknown model",
        )


def ensure_scorer_ready(scorer: RiskScorer) -> None:
    """Reject readiness checks while the configured scoring backend is unavailable."""
    if not scorer.ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": MODEL_BACKEND_NOT_READY_CODE},
        )


def parse_inference_request(
    body: InferRequestDto,
    *,
    request_id: str,
) -> PredictionRequest:
    """Translate one valid KServe tensor document into canonical serving input."""
    if len(body.inputs) != 1:
        raise invalid_inference_request("exactly one input tensor is required")
    tensor = body.inputs[0]
    if tensor.name != FEATURE_INPUT_NAME or tensor.datatype != FEATURE_INPUT_DATATYPE:
        raise invalid_inference_request(
            "input tensor must be named features with BYTES datatype"
        )
    if tensor.shape != [1] or len(tensor.data) != 1:
        raise invalid_inference_request("input tensor shape must be [1]")
    try:
        features = FEATURES_DOCUMENT.validate_json(tensor.data[0])
    except (TypeError, ValidationError, ValueError) as error:
        raise invalid_inference_request(
            "features tensor must contain one JSON object"
        ) from error
    return PredictionRequest(
        request_id=request_id,
        features=tuple(features.items()),
        scenario=KSERVE_SCENARIO,
    )


def render_inference_response(
    *,
    model_name: str,
    inference_id: str | None,
    scored: ScoredRisk,
) -> InferResponseDto:
    """Translate one canonical score into the KServe V2 output tensor contract."""
    return InferResponseDto(
        model_name=model_name,
        model_version=scored.model.version,
        id=inference_id,
        outputs=[
            InferOutputDto(
                name=RISK_SCORE_OUTPUT_NAME,
                shape=list(RISK_SCORE_OUTPUT_SHAPE),
                datatype=RISK_SCORE_OUTPUT_DATATYPE,
                data=[[scored.score]],
            )
        ],
    )


def invalid_inference_request(message: str) -> HTTPException:
    """Create the stable KServe V2 client-error response for invalid input."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": INVALID_INFERENCE_REQUEST_CODE, "message": message},
    )
