"""Prediction event sink port."""

from __future__ import annotations

from typing import Protocol

from ai_quality.serving.domain.prediction_response import PredictionResponse


class PredictionEventSink(Protocol):
    """Record prediction events for later observability labs."""

    def record(self, response: PredictionResponse) -> None:
        """Record one prediction response."""
        ...
