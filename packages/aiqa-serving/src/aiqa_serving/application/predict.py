"""Validate canonical model input and produce one risk prediction."""

from aiqa_core.domain import FeatureSet

from aiqa_serving.domain import PredictionEvent, PredictionRequest, RiskPrediction
from aiqa_serving.ports import PredictionEventRecorder, RiskScorer


class PredictRisk:
    def __init__(
        self,
        feature_set: FeatureSet,
        scorer: RiskScorer,
        event_recorder: PredictionEventRecorder,
    ) -> None:
        self._feature_set = feature_set
        self._scorer = scorer
        self._event_recorder = event_recorder

    def execute(self, request: PredictionRequest) -> RiskPrediction:
        values = dict(request.features)
        expected = set(self._feature_set.feature_names)
        actual = set(values)
        if actual != expected:
            raise ValueError(
                f"model input contract mismatch: missing={sorted(expected - actual)}, "
                f"extra={sorted(actual - expected)}"
            )
        forbidden_nulls = [
            feature.name
            for feature in self._feature_set.features
            if not feature.nullable and values[feature.name] is None
        ]
        if forbidden_nulls:
            raise ValueError(f"non-nullable model features are null: {forbidden_nulls}")
        ordered = tuple(
            (name, values[name]) for name in self._feature_set.feature_names
        )
        prediction = RiskPrediction(
            request_id=request.request_id,
            model=self._scorer.identity,
            score=self._scorer.score(ordered),
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
