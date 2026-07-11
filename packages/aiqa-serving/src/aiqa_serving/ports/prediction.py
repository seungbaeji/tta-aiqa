"""Online scoring and event recording ports."""

from typing import Protocol

from aiqa_serving.domain import (
    FeatureValue,
    ModelIdentity,
    PredictionEvent,
)


class RiskScorer(Protocol):
    @property
    def identity(self) -> ModelIdentity: ...

    def ready(self) -> bool: ...

    def score(self, features: tuple[tuple[str, FeatureValue], ...]) -> float: ...


class PredictionEventRecorder(Protocol):
    def record(self, event: PredictionEvent) -> None: ...
