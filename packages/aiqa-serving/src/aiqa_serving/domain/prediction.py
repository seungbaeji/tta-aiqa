"""Online mortality-risk prediction values and invariants."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

FeatureValue = str | float | int | bool | None


@dataclass(frozen=True)
class PredictionLabels:
    """Configured labels for positive and negative model outcomes."""

    positive: str
    negative: str

    def __post_init__(self) -> None:
        labels = (self.positive, self.negative)
        if any(
            not isinstance(label, str) or not label or label != label.strip()
            for label in labels
        ):
            raise ValueError("prediction labels must be non-empty trimmed strings")
        if self.positive == self.negative:
            raise ValueError("prediction labels must be distinct")


@dataclass(frozen=True)
class ModelIdentity:
    """Stable identity and decision threshold for one loaded scoring model."""

    profile: str
    version: str
    threshold: float

    def __post_init__(self) -> None:
        identifiers = (self.profile, self.version)
        if any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in identifiers
        ):
            raise ValueError(
                "model profile and version must be non-empty trimmed strings"
            )
        if (
            isinstance(self.threshold, bool)
            or not isinstance(self.threshold, (int, float))
            or not isfinite(self.threshold)
            or not 0 < self.threshold < 1
        ):
            raise ValueError("model threshold must be between zero and one")


@dataclass(frozen=True)
class PredictionRequest:
    """Canonical internal request passed to a scoring capability."""

    request_id: str
    features: tuple[tuple[str, FeatureValue], ...]
    scenario: str = "unspecified"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.request_id, str)
            or not self.request_id
            or self.request_id != self.request_id.strip()
        ):
            raise ValueError("request ID must be a non-empty trimmed string")
        if (
            not isinstance(self.scenario, str)
            or not self.scenario
            or self.scenario != self.scenario.strip()
        ):
            raise ValueError("prediction scenario must be a non-empty trimmed string")
        if not isinstance(self.features, tuple) or not self.features:
            raise ValueError("prediction request requires feature values")
        if any(not isinstance(item, tuple) or len(item) != 2 for item in self.features):
            raise ValueError("prediction features must contain name-value pairs")
        names = [name for name, _ in self.features]
        if any(
            not isinstance(name, str) or not name or name != name.strip()
            for name in names
        ):
            raise ValueError(
                "prediction feature names must be non-empty trimmed strings"
            )
        if len(names) != len(set(names)):
            raise ValueError("prediction feature names must be unique")


@dataclass(frozen=True)
class ScoredRisk:
    """Validated score and model identity before delivery-specific labeling."""

    request_id: str
    model: ModelIdentity
    score: float
    missing_feature_count: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not isfinite(self.score)
            or not 0 <= self.score <= 1
        ):
            raise ValueError("risk score must be between zero and one")
        if (
            not isinstance(self.missing_feature_count, int)
            or isinstance(self.missing_feature_count, bool)
            or self.missing_feature_count < 0
        ):
            raise ValueError("missing feature count must be non-negative")


@dataclass(frozen=True)
class RiskPrediction:
    """Labeled risk result returned by the public Risk API capability."""

    request_id: str
    model: ModelIdentity
    score: float
    label: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not isfinite(self.score)
            or not 0 <= self.score <= 1
        ):
            raise ValueError("risk score must be between zero and one")
        if (
            not isinstance(self.label, str)
            or not self.label
            or self.label != self.label.strip()
        ):
            raise ValueError("prediction label must be a non-empty trimmed string")

    @property
    def positive(self) -> bool:
        """Return whether the score meets this model identity's decision threshold."""
        return self.score >= self.model.threshold


@dataclass(frozen=True)
class PredictionEvent:
    """Domain event emitted after a labeled risk prediction."""

    request_id: str
    model_profile: str
    model_version: str
    score: float
    threshold: float
    prediction: str
    missing_feature_count: int
    scenario: str = "unspecified"

    def __post_init__(self) -> None:
        identifiers = (
            self.request_id,
            self.model_profile,
            self.model_version,
            self.prediction,
            self.scenario,
        )
        if any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in identifiers
        ):
            raise ValueError(
                "prediction event identifiers must be non-empty trimmed strings"
            )
        numeric_values = (self.score, self.threshold)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or not 0 <= value <= 1
            for value in numeric_values
        ):
            raise ValueError(
                "prediction event score and threshold must be finite values"
            )
        if not 0 < self.threshold < 1:
            raise ValueError("prediction event threshold must be between zero and one")
        if (
            not isinstance(self.missing_feature_count, int)
            or isinstance(self.missing_feature_count, bool)
            or self.missing_feature_count < 0
        ):
            raise ValueError(
                "prediction event missing-feature count must be non-negative"
            )
