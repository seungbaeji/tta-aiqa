"""Framework-independent prediction use case tests."""

from dataclasses import dataclass, field

import pytest
from aiqa_core.domain import FeatureDefinition, FeatureSet, FeatureType
from aiqa_serving.application import (
    complete_feature_values,
    predict_risk,
    score_risk,
)
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
    result = predict_risk(
        PredictionRequest(
            request_id="request-1",
            features=(("heart_rate", None), ("age", 67.0)),
        ),
        feature_set=contract(),
        scorer=scorer,
        event_recorder=sink,
        labels=PredictionLabels("high_risk", "low_risk"),
    )

    assert scorer.received == (("age", 67.0), ("heart_rate", None))
    assert result.label == "high_risk"
    assert sink.events[0].model_profile == "candidate-b"
    assert sink.events[0].missing_feature_count == 1


def physionet_like_contract() -> FeatureSet:
    return FeatureSet(
        schema_version=1,
        name="public-dto",
        target="target",
        features=(
            FeatureDefinition("age", FeatureType.FLOAT, True),
            FeatureDefinition("age__missing", FeatureType.BOOLEAN, False),
            FeatureDefinition("weight__min", FeatureType.FLOAT, True),
            FeatureDefinition("weight__mean", FeatureType.FLOAT, True),
            FeatureDefinition("weight__missing", FeatureType.BOOLEAN, False),
        ),
    )


def test_complete_feature_values_fills_omitted_nullable_and_missing_flags() -> None:
    completed = complete_feature_values({"age": 68.0}, physionet_like_contract())

    assert completed["age"] == 68.0
    assert completed["age__missing"] is False
    assert completed["weight__min"] is None
    assert completed["weight__mean"] is None
    assert completed["weight__missing"] is True


def test_complete_feature_values_keeps_extras_and_required_omissions() -> None:
    completed = complete_feature_values(
        {"heart_rate": 80.0, "unexpected": 1.0},
        contract(),
    )

    assert completed["heart_rate"] == 80.0
    assert completed["unexpected"] == 1.0
    assert "age" not in completed


def test_prediction_rejects_missing_extra_and_forbidden_null_features() -> None:
    with pytest.raises(ValueError, match="contract mismatch"):
        predict_risk(
            PredictionRequest(
                request_id="request-1",
                features=(("age", 67.0), ("unexpected", 1.0)),
            ),
            feature_set=contract(),
            scorer=StubScorer(),
            event_recorder=RecordingSink(),
            labels=PredictionLabels("high_risk", "low_risk"),
        )
    with pytest.raises(ValueError, match="non-nullable"):
        predict_risk(
            PredictionRequest(
                request_id="request-2",
                features=(("age", None), ("heart_rate", 80.0)),
            ),
            feature_set=contract(),
            scorer=StubScorer(),
            event_recorder=RecordingSink(),
            labels=PredictionLabels("high_risk", "low_risk"),
        )


def test_prediction_uses_configured_outcome_labels() -> None:
    result = predict_risk(
        PredictionRequest(
            request_id="request-3",
            features=(("age", 67.0), ("heart_rate", None)),
        ),
        feature_set=contract(),
        scorer=StubScorer(),
        event_recorder=RecordingSink(),
        labels=PredictionLabels("positive-risk", "negative-risk"),
    )

    assert result.label == "positive-risk"


def test_score_risk_is_reusable_without_api_labels_or_event_recording() -> None:
    scorer = StubScorer()

    result = score_risk(
        PredictionRequest(
            request_id="kserve-request-1",
            features=(("heart_rate", None), ("age", 67.0)),
            scenario="kserve",
        ),
        feature_set=contract(),
        scorer=scorer,
    )

    assert result.request_id == "kserve-request-1"
    assert result.model == scorer.identity
    assert result.missing_feature_count == 1


def test_score_risk_preserves_a_categorical_feature_value() -> None:
    feature_set = FeatureSet(
        schema_version=1,
        name="category-test",
        target="target",
        features=(FeatureDefinition("gender", FeatureType.CATEGORY, False),),
    )
    scorer = StubScorer()

    score_risk(
        PredictionRequest(
            request_id="category-request",
            features=(("gender", "female"),),
        ),
        feature_set=feature_set,
        scorer=scorer,
    )

    assert scorer.received == (("gender", "female"),)
