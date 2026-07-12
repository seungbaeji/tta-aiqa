"""Framework-independent model lifecycle use cases."""

from aiqa_model.domain import BenchmarkResult, FeatureDiagnostics
from aiqa_model.ports import FittedModels, ModelBenchmark


class DevelopModels:
    """Run the train/valid development benchmark through its port."""

    def __init__(self, benchmark: ModelBenchmark) -> None:
        self._benchmark = benchmark

    def execute(self) -> BenchmarkResult:
        """Return validation evidence without accessing the sealed test role."""
        return self._benchmark.development()


class DiagnoseFeatures:
    """Run feature diagnostics on development roles."""

    def __init__(self, benchmark: ModelBenchmark) -> None:
        self._benchmark = benchmark

    def execute(
        self, *, baseline_profile: str, candidate_profile: str
    ) -> FeatureDiagnostics:
        """Return diagnostics for the selected baseline and candidate profiles."""
        return self._benchmark.feature_diagnostics(
            baseline_profile=baseline_profile,
            candidate_profile=candidate_profile,
        )


class FitModelBundles:
    """Fit named model bundles using only development data."""

    def __init__(self, benchmark: ModelBenchmark) -> None:
        self._benchmark = benchmark

    def execute(self, profiles: tuple[str, ...]) -> FittedModels:
        """Return a typed collection of fitted profile models."""
        return self._benchmark.fit_bundles(profiles)


class ConfirmFrozenModels:
    """Evaluate previously fitted bundles against the sealed test role once."""

    def __init__(self, benchmark: ModelBenchmark) -> None:
        self._benchmark = benchmark

    def execute(
        self, *, sealed_test_token: str, fitted_models: FittedModels
    ) -> BenchmarkResult:
        """Confirm frozen models without refitting them."""
        return self._benchmark.final_confirmation(
            sealed_test_token=sealed_test_token,
            fitted_pipelines=fitted_models,
        )
