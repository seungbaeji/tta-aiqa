"""Train-serving skew checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkewCheckResult:
    """Feature and threshold compatibility result."""

    missing_serving_features: tuple[str, ...]
    unexpected_serving_features: tuple[str, ...]
    order_matches: bool
    threshold_matches: bool

    @property
    def passed(self) -> bool:
        """Return whether train and serving settings are compatible."""
        return (
            not self.missing_serving_features
            and not self.unexpected_serving_features
            and self.order_matches
            and self.threshold_matches
        )


# docs:start verify_feature_compatibility
def verify_feature_compatibility(
    training_features: list[str],
    serving_features: list[str],
    training_threshold: float,
    serving_threshold: float,
) -> SkewCheckResult:
    """Check feature and threshold compatibility for serving."""
    training_feature_set = set(training_features)
    serving_feature_set = set(serving_features)

    return SkewCheckResult(
        missing_serving_features=tuple(
            feature
            for feature in training_features
            if feature not in serving_feature_set
        ),
        unexpected_serving_features=tuple(
            feature
            for feature in serving_features
            if feature not in training_feature_set
        ),
        order_matches=training_features == serving_features,
        threshold_matches=training_threshold == serving_threshold,
    )
# docs:end verify_feature_compatibility
