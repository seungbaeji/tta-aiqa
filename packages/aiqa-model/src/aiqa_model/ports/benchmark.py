"""Model development engine boundaries and fitted-model contracts."""

from dataclasses import dataclass
from typing import Any, Protocol

from aiqa_model.domain import BenchmarkResult, FeatureDiagnostics


class FittedModel(Protocol):
    """Minimum scoring surface required by the model lifecycle."""

    def predict_proba(self, values: Any) -> Any:
        """Return positive-class probabilities for supplied features."""


@dataclass(frozen=True)
class FittedModels:
    """Named fitted models passed from bootstrap fitting to final evaluation."""

    items: tuple[tuple[str, FittedModel], ...]

    def __post_init__(self) -> None:
        names = tuple(name for name, _ in self.items)
        if not names or any(not name for name in names):
            raise ValueError("fitted models require at least one named model")
        if len(names) != len(set(names)):
            raise ValueError("fitted model names must be unique")
        if names != tuple(sorted(names)):
            raise ValueError("fitted model names must be sorted")

    @classmethod
    def from_mapping(cls, models: dict[str, FittedModel]) -> "FittedModels":
        """Create a deterministic named collection from a profile mapping."""
        return cls(tuple(sorted(models.items())))

    @property
    def names(self) -> tuple[str, ...]:
        """Return fitted profile names in deterministic order."""
        return tuple(name for name, _ in self.items)

    def get(self, name: str) -> FittedModel:
        """Return the model for a profile or raise a descriptive error."""
        for profile, model in self.items:
            if profile == name:
                return model
        raise KeyError(f"fitted model profile does not exist: {name}")


class ModelBenchmark(Protocol):
    def development(self) -> BenchmarkResult: ...

    def feature_diagnostics(
        self, *, baseline_profile: str, candidate_profile: str
    ) -> FeatureDiagnostics: ...

    def fit_bundles(self, profiles: tuple[str, ...]) -> FittedModels: ...

    def final_confirmation(
        self,
        *,
        sealed_test_token: str | None,
        fitted_pipelines: FittedModels | None = None,
    ) -> BenchmarkResult: ...
