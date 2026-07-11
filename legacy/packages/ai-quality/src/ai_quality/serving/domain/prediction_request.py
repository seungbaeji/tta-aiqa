"""Prediction request domain object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PredictionRequest:
    """Model input request used inside the serving application."""

    request_id: str
    features: dict[str, float]

    @classmethod
    def from_mapping(
        cls,
        request_id: str,
        payload: dict[str, Any],
        feature_columns: list[str],
    ) -> PredictionRequest:
        """Build a request from a flat payload and expected feature list."""
        return cls(
            request_id=request_id,
            features={
                column: float(payload[column])
                for column in feature_columns
            },
        )
