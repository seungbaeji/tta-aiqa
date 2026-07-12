"""Validate canonical model input and produce one risk prediction."""

import math
from typing import Any

from aiqa_core.domain import FeatureSet, FeatureType

from aiqa_serving.domain import (
    FeatureValue,
    PredictionEvent,
    PredictionLabels,
    PredictionRequest,
    RiskPrediction,
)
from aiqa_serving.ports import PredictionEventRecorder, RiskScorer


def validate_feature_values(
    payload: dict[str, Any], feature_set: FeatureSet
) -> tuple[tuple[str, FeatureValue], ...]:
    """Validate and order one payload according to the canonical feature contract."""
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


class PredictRisk:
    def __init__(
        self,
        feature_set: FeatureSet,
        scorer: RiskScorer,
        event_recorder: PredictionEventRecorder,
        labels: PredictionLabels,
    ) -> None:
        self._feature_set = feature_set
        self._scorer = scorer
        self._event_recorder = event_recorder
        self._labels = labels

    def execute(self, request: PredictionRequest) -> RiskPrediction:
        ordered = validate_feature_values(dict(request.features), self._feature_set)
        score = self._scorer.score(ordered)
        prediction = RiskPrediction(
            request_id=request.request_id,
            model=self._scorer.identity,
            score=score,
            label=self._labels.positive
            if score >= self._scorer.identity.threshold
            else self._labels.negative,
        )
        self._event_recorder.record(
            PredictionEvent(
                request_id=prediction.request_id,
                model_profile=prediction.model.profile,
                model_version=prediction.model.version,
                score=prediction.score,
                threshold=prediction.model.threshold,
                prediction=prediction.label,
                missing_feature_count=sum(value is None for _, value in ordered),
                scenario=request.scenario,
            )
        )
        return prediction
