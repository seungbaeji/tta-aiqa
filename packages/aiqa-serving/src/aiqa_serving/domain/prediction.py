"""Online mortality-risk prediction values and invariants."""

from __future__ import annotations

from dataclasses import dataclass

FeatureValue = float | int | bool | None


@dataclass(frozen=True)
class PredictionLabels:
    """Configured labels for positive and negative model outcomes."""

    positive: str
    negative: str

    def __post_init__(self) -> None:
        if not self.positive or not self.negative:
            raise ValueError("prediction labels are required")
        if self.positive == self.negative:
            raise ValueError("prediction labels must be distinct")


@dataclass(frozen=True)
class ModelIdentity:
    profile: str
    version: str
    threshold: float

    def __post_init__(self) -> None:
        if not self.profile or not self.version:
            raise ValueError("model profile and version are required")
        if not 0 < self.threshold < 1:
            raise ValueError("model threshold must be between zero and one")


@dataclass(frozen=True)
class PredictionRequest:
    request_id: str
    features: tuple[tuple[str, FeatureValue], ...]
    scenario: str = "unspecified"

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request ID is required")
        if not self.scenario:
            raise ValueError("prediction scenario is required")
        names = [name for name, _ in self.features]
        if len(names) != len(set(names)):
            raise ValueError("prediction feature names must be unique")


@dataclass(frozen=True)
class RiskPrediction:
    request_id: str
    model: ModelIdentity
    score: float
    label: str

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("risk score must be between zero and one")
        if not self.label:
            raise ValueError("prediction label is required")

    @property
    def positive(self) -> bool:
        return self.score >= self.model.threshold

@dataclass(frozen=True)
class PredictionEvent:
    request_id: str
    model_profile: str
    model_version: str
    score: float
    threshold: float
    prediction: str
    missing_feature_count: int
    scenario: str = "unspecified"
