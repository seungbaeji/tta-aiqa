"""Focused outbound capabilities required by model lifecycle use cases."""

from typing import Protocol

from aiqa_model.domain import (
    BenchmarkResult,
    FeatureDiagnostics,
    FeatureDiagnosticsRequest,
    ModelProfileSelection,
)
from aiqa_model.ports.fitted_models import FittedModels


class DevelopmentModelEvaluator(Protocol):
    """Evaluate selected configured profiles using development data only."""

    def evaluate_development(
        self, selection: ModelProfileSelection
    ) -> BenchmarkResult:
        """Return validation evidence for the requested profiles."""


class FeatureDiagnostician(Protocol):
    """Generate feature evidence for one baseline and candidate comparison."""

    def produce_feature_diagnostics(
        self, request: FeatureDiagnosticsRequest
    ) -> FeatureDiagnostics:
        """Return diagnostics produced without accessing the sealed test role."""


class FrozenModelFitter(Protocol):
    """Fit selected profiles on frozen development roles."""

    def fit_models(self, selection: ModelProfileSelection) -> FittedModels:
        """Return opaque fitted artifacts named by the requested profiles."""


class FrozenModelEvaluator(Protocol):
    """Score supplied frozen artifacts against the sealed test role."""

    def evaluate_frozen_models(
        self,
        selection: ModelProfileSelection,
        fitted_models: FittedModels,
    ) -> BenchmarkResult:
        """Return final evidence without fitting or selecting a new model."""
