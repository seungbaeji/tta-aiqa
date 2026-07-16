"""Online scoring and event recording ports."""

from typing import Protocol

from aiqa_serving.domain import (
    FeatureValue,
    ModelIdentity,
    PredictionEvent,
)


class RiskScorer(Protocol):
    """Score canonical ordered feature values with one model backend."""

    @property
    def identity(self) -> ModelIdentity:
        """Return the identity of the model that will score requests."""
        ...

    def ready(self) -> bool:
        """Return whether the backend can currently serve the declared model."""
        ...

    def score(self, features: tuple[tuple[str, FeatureValue], ...]) -> float:
        """Return the positive-class probability for canonical ordered features."""
        ...


class PredictionEventRecorder(Protocol):
    """Record one completed prediction domain event in an outbound sink."""

    def record(self, event: PredictionEvent) -> None:
        """Persist or emit the supplied model-aware prediction event."""
        ...
