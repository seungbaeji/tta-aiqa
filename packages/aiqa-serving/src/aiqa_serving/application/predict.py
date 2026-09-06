"""Validate canonical model input and produce one risk prediction."""

import math

from aiqa_core.domain import FeatureSet, FeatureType

from aiqa_serving.domain import (
    FeatureValue,
    PredictionEvent,
    PredictionLabels,
    PredictionRequest,
    RiskPrediction,
    ScoredRisk,
)
from aiqa_serving.ports import PredictionEventRecorder, RiskScorer

MISSING_INDICATOR_SUFFIX = "__missing"


def complete_feature_values(
    features: dict[str, FeatureValue],
    feature_set: FeatureSet,
) -> dict[str, FeatureValue]:
    """Fill omitted public fields from the feature contract without dropping extras.

    Nullable measurements default to null. A missing-indicator defaults to false
    when a related value is present, otherwise true. Non-nullable fields that
    are not missing-indicators stay omitted so later validation can reject them.
    """
    payload = dict(features)
    for feature in feature_set.features:
        if feature.name in payload:
            continue
        if feature.name.endswith(MISSING_INDICATOR_SUFFIX):
            payload[feature.name] = _inferred_missing_flag(feature.name, payload)
        elif feature.nullable:
            payload[feature.name] = None
    return payload


def _inferred_missing_flag(
    flag_name: str, payload: dict[str, FeatureValue]
) -> bool:
    prefix = flag_name[: -len(MISSING_INDICATOR_SUFFIX)]
    for name, value in payload.items():
        if name.endswith(MISSING_INDICATOR_SUFFIX):
            continue
        if value is None:
            continue
        if name == prefix or name.startswith(f"{prefix}__"):
            return False
    return True


def validate_feature_values(
    features: tuple[tuple[str, FeatureValue], ...], feature_set: FeatureSet
) -> tuple[tuple[str, FeatureValue], ...]:
    """Validate and order one internal feature tuple by the canonical contract."""
    payload = dict(features)
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
        elif feature.dtype is FeatureType.CATEGORY:
            if isinstance(value, bool) or not isinstance(value, str | int | float):
                raise ValueError(f"category feature has invalid type: {feature.name}")
        values.append((feature.name, value))
    return tuple(values)


def score_risk(
    request: PredictionRequest,
    *,
    feature_set: FeatureSet,
    scorer: RiskScorer,
) -> ScoredRisk:
    """Validate and score one canonical request without delivery-specific effects."""
    ordered = validate_feature_values(request.features, feature_set)
    return ScoredRisk(
        request_id=request.request_id,
        model=scorer.identity,
        score=scorer.score(ordered),
        missing_feature_count=sum(value is None for _, value in ordered),
    )


def predict_risk(
    request: PredictionRequest,
    *,
    feature_set: FeatureSet,
    scorer: RiskScorer,
    event_recorder: PredictionEventRecorder,
    labels: PredictionLabels,
) -> RiskPrediction:
    """Score a request, attach the configured label, and emit its domain event."""
    scored = score_risk(request, feature_set=feature_set, scorer=scorer)
    prediction = RiskPrediction(
        request_id=scored.request_id,
        model=scored.model,
        score=scored.score,
        label=(
            labels.positive
            if scored.score >= scored.model.threshold
            else labels.negative
        ),
    )
    event_recorder.record(
        PredictionEvent(
            request_id=prediction.request_id,
            model_profile=prediction.model.profile,
            model_version=prediction.model.version,
            score=prediction.score,
            threshold=prediction.model.threshold,
            prediction=prediction.label,
            missing_feature_count=scored.missing_feature_count,
            scenario=request.scenario,
        )
    )
    return prediction
