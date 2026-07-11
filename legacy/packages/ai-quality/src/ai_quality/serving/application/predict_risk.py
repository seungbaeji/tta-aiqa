"""Prediction use case."""

from __future__ import annotations

from dataclasses import dataclass

from ai_quality.common.labels import NEGATIVE_LABEL, POSITIVE_LABEL
from ai_quality.serving.domain.prediction_request import PredictionRequest
from ai_quality.serving.domain.prediction_response import PredictionResponse
from ai_quality.serving.ports.prediction_event_sink import PredictionEventSink
from ai_quality.serving.ports.scoring_model import ScoringModel


@dataclass(frozen=True)
class PredictRisk:
    """Convert request features into score and prediction."""

    model: ScoringModel
    threshold: float
    model_version: str
    event_sink: PredictionEventSink | None = None

    # docs:start predict_risk
    def run(self, request: PredictionRequest) -> PredictionResponse:
        """Return prediction response for one request."""
        score = self.model.score_one(request.features)
        prediction = POSITIVE_LABEL if score >= self.threshold else NEGATIVE_LABEL
        response = PredictionResponse(
            request_id=request.request_id,
            model_version=self.model_version,
            score=score,
            threshold=self.threshold,
            prediction=prediction,
        )

        if self.event_sink is not None:
            self.event_sink.record(response)

        return response
    # docs:end predict_risk
