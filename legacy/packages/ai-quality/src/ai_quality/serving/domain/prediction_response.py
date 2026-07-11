"""Prediction response domain object."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PredictionResponse:
    """Response returned by the prediction use case."""

    request_id: str
    model_version: str
    score: float
    threshold: float
    prediction: str

    def to_dict(self) -> dict[str, str | float]:
        """Return a JSON-serializable dictionary."""
        return asdict(self)
