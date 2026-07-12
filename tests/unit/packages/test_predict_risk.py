"""Framework-independent prediction use case tests."""

from dataclasses import dataclass, field

import pytest
from aiqa_core.domain import FeatureDefinition, FeatureSet, FeatureType
from aiqa_serving.application import PredictRisk
from aiqa_serving.domain import (
    FeatureValue,
    ModelIdentity,
    PredictionEvent,
    PredictionLabels,
    PredictionRequest,
)


@dataclass
class StubScorer:
    identity: ModelIdentity = ModelIdentity("candidate-b", "v2-abc", 0.35)
    received: tuple[tuple[str, FeatureValue], ...] = ()

    def ready(self) -> bool:
        return True

    def score(self, features: tuple[tuple[str, FeatureValue], ...]) -> float:
        self.received = features
        return 0.72


@dataclass
class RecordingSink:
    events: list[PredictionEvent] = field(default_factory=list)

    def record(self, event: PredictionEvent) -> None:
        self.events.append(event)


def contract() -> FeatureSet:
    return FeatureSet(
        schema_version=1,
        name="test-v1",
        target="target",
        features=(
            FeatureDefinition("age", FeatureType.FLOAT, False),
            FeatureDefinition("heart_rate", FeatureType.FLOAT, True),
        ),
    )


def test_prediction_orders_features_and_records_model_aware_event() -> None:
    scorer = StubScorer()
    sink = RecordingSink()
    use_case = PredictRisk(
        contract(), scorer, sink, PredictionLabels("high_risk", "low_risk")
    )

    result = use_case.execute(
        PredictionRequest(
            request_id="request-1",
            features=(("heart_rate", None), ("age", 67.0)),
        )
    )

    assert scorer.received == (("age", 67.0), ("heart_rate", None))
    assert result.label == "high_risk"
    assert sink.events[0].model_profile == "candidate-b"
    assert sink.events[0].missing_feature_count == 1


def test_prediction_rejects_missing_extra_and_forbidden_null_features() -> None:
    use_case = PredictRisk(
        contract(),
        StubScorer(),
        RecordingSink(),
        PredictionLabels("high_risk", "low_risk"),
    )

    with pytest.raises(ValueError, match="contract mismatch"):
        use_case.execute(
            PredictionRequest(
                request_id="request-1",
                features=(("age", 67.0), ("unexpected", 1.0)),
            )
        )
    with pytest.raises(ValueError, match="non-nullable"):
        use_case.execute(
            PredictionRequest(
                request_id="request-2",
                features=(("age", None), ("heart_rate", 80.0)),
            )
        )


def test_prediction_uses_configured_outcome_labels() -> None:
    use_case = PredictRisk(
        contract(),
        StubScorer(),
        RecordingSink(),
        PredictionLabels("positive-risk", "negative-risk"),
    )

    result = use_case.execute(
        PredictionRequest(
            request_id="request-3",
            features=(("age", 67.0), ("heart_rate", None)),
        )
    )

    assert result.label == "positive-risk"
