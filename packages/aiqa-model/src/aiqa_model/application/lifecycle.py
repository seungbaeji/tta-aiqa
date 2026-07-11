"""Framework-independent model lifecycle use cases."""

from aiqa_model.domain import BenchmarkResult
from aiqa_model.ports import ModelBenchmark


class DevelopModels:
    def __init__(self, benchmark: ModelBenchmark) -> None:
        self._benchmark = benchmark

    def execute(self) -> BenchmarkResult:
        return self._benchmark.development()


class DiagnoseFeatures:
    def __init__(self, benchmark: ModelBenchmark) -> None:
        self._benchmark = benchmark

    def execute(
        self, *, baseline_profile: str, candidate_profile: str
    ) -> dict[str, object]:
        return self._benchmark.feature_diagnostics(
            baseline_profile=baseline_profile,
            candidate_profile=candidate_profile,
        )


class FitModelBundles:
    def __init__(self, benchmark: ModelBenchmark) -> None:
        self._benchmark = benchmark

    def execute(self, profiles: tuple[str, ...]) -> dict[str, object]:
        return self._benchmark.fit_bundles(profiles)


class ConfirmFrozenModels:
    def __init__(self, benchmark: ModelBenchmark) -> None:
        self._benchmark = benchmark

    def execute(
        self, *, sealed_test_token: str, fitted_models: dict[str, object]
    ) -> BenchmarkResult:
        return self._benchmark.final_confirmation(
            sealed_test_token=sealed_test_token,
            fitted_pipelines=fitted_models,
        )
