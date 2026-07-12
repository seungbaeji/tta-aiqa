"""KServe V2 protocol translation tests without a FastAPI server runtime."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from aiqa_serving.domain import ModelIdentity, PredictionRequest, ScoredRisk
from fastapi import HTTPException, status
from kserve_predictor.adapters.kserve_v2 import (
    INVALID_INFERENCE_REQUEST_CODE,
    MODEL_BACKEND_NOT_READY_CODE,
    InferInputDto,
    InferRequestDto,
    ensure_scorer_ready,
    parse_inference_request,
    render_inference_response,
    validate_requested_model,
)


def inference_request(*, shape: list[int] | None = None) -> InferRequestDto:
    """Return one KServe request DTO with a JSON-encoded feature object."""
    return InferRequestDto(
        id="inference-123",
        inputs=[
            InferInputDto(
                name="features",
                shape=shape or [1],
                datatype="BYTES",
                data=['{"age":68.0,"age__missing":false}'],
            )
        ],
    )


@dataclass(frozen=True)
class UnreadyScorer:
    """Satisfy the scorer port while reporting an unavailable backend."""

    @property
    def identity(self) -> ModelIdentity:
        """Return an identity required by the scorer port contract."""
        return ModelIdentity(profile="baseline", version="baseline-v1", threshold=0.5)

    def ready(self) -> bool:
        """Report that this fixture backend cannot serve requests."""
        return False

    def score(self, _: tuple[tuple[str, object], ...]) -> float:
        """Satisfy the scorer port outside this readiness test's scope."""
        return 0.0


def test_protocol_parser_creates_canonical_request_with_kserve_scenario() -> None:
    """The adapter owns tensor parsing but delegates feature policy to serving."""
    request = parse_inference_request(
        inference_request(),
        request_id="request-456",
    )

    assert request == PredictionRequest(
        request_id="request-456",
        features=(("age", 68.0), ("age__missing", False)),
        scenario="kserve",
    )


def test_protocol_parser_rejects_invalid_tensor_shape_with_kserve_error() -> None:
    """Malformed V2 tensor metadata becomes the stable client error contract."""
    with pytest.raises(HTTPException) as raised:
        parse_inference_request(inference_request(shape=[2]), request_id="request-456")

    assert raised.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert raised.value.detail["code"] == INVALID_INFERENCE_REQUEST_CODE


def test_protocol_response_and_availability_checks_preserve_v2_contract() -> None:
    """Readiness and output tensor construction remain delivery-specific behavior."""
    scored = ScoredRisk(
        request_id="request-456",
        model=ModelIdentity(profile="baseline", version="baseline-v1", threshold=0.5),
        score=0.73,
        missing_feature_count=0,
    )
    response = render_inference_response(
        model_name="mortality-risk",
        inference_id="inference-123",
        scored=scored,
    )

    assert response.model_version == "baseline-v1"
    assert response.outputs[0].model_dump() == {
        "name": "risk_score",
        "shape": [1, 1],
        "datatype": "FP64",
        "data": [[0.73]],
    }
    with pytest.raises(HTTPException) as raised:
        ensure_scorer_ready(UnreadyScorer())
    assert raised.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert raised.value.detail == {"code": MODEL_BACKEND_NOT_READY_CODE}


def test_unknown_model_is_rejected_before_scoring() -> None:
    """A route for another model cannot reach this process's scoring operation."""
    with pytest.raises(HTTPException) as raised:
        validate_requested_model("other-model", "mortality-risk")

    assert raised.value.status_code == status.HTTP_404_NOT_FOUND
