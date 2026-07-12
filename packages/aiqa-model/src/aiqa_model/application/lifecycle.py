"""Framework-independent model lifecycle use cases."""

from aiqa_model.domain import BenchmarkResult, FeatureDiagnostics
from aiqa_model.ports import FittedModels, ModelBenchmark


def develop_models(*, benchmark: ModelBenchmark) -> BenchmarkResult:
    """Return validation evidence without accessing the sealed test role."""
    return benchmark.development()


def diagnose_features(
    *,
    benchmark: ModelBenchmark,
    baseline_profile: str,
    candidate_profile: str,
) -> FeatureDiagnostics:
    """Return diagnostics for the selected baseline and candidate profiles."""
    return benchmark.feature_diagnostics(
        baseline_profile=baseline_profile,
        candidate_profile=candidate_profile,
    )


def fit_model_bundles(
    *, benchmark: ModelBenchmark, profiles: tuple[str, ...]
) -> FittedModels:
    """Fit named model bundles using only development data."""
    return benchmark.fit_bundles(profiles)


def confirm_frozen_models(
    *,
    benchmark: ModelBenchmark,
    sealed_test_token: str,
    fitted_models: FittedModels,
) -> BenchmarkResult:
    """Confirm frozen models without refitting them."""
    return benchmark.final_confirmation(
        sealed_test_token=sealed_test_token,
        fitted_pipelines=fitted_models,
    )
