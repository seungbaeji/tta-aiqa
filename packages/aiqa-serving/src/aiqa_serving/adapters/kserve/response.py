"""Pydantic validation and score extraction for KServe V2 inference responses."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KServeOutputDocument(BaseModel):
    """One output tensor returned by a KServe V2 inference response."""

    model_config = ConfigDict(extra="allow", frozen=True)

    name: str
    data: Any


class KServeInferResponseDocument(BaseModel):
    """Validated subset of the KServe V2 response used by this scoring adapter."""

    model_config = ConfigDict(extra="allow", frozen=True)

    model_name: str
    model_version: str
    outputs: tuple[KServeOutputDocument, ...] = Field(min_length=1)


def positive_score(document: Mapping[str, Any]) -> float:
    """Validate a KServe response and extract its positive-class probability."""
    response = KServeInferResponseDocument.model_validate(document)
    return positive_score_from_data(response.outputs[0].data)


def positive_score_from_data(data: object) -> float:
    """Extract the positive class from a nested binary-class KServe output tensor."""
    value = data
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, list) and len(value) == 2:
        value = value[1]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("KServe response does not contain a positive-class score")
    score = float(value)
    if not isfinite(score) or not 0 <= score <= 1:
        raise ValueError("KServe positive-class score is outside [0, 1]")
    return score
