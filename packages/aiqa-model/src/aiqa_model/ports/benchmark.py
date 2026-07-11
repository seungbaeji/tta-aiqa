"""Model development engine boundary."""

from typing import Protocol

from aiqa_model.domain import BenchmarkResult


class ModelBenchmark(Protocol):
    def development(self) -> BenchmarkResult: ...

    def feature_diagnostics(
        self, *, baseline_profile: str, candidate_profile: str
    ) -> dict[str, object]: ...

    def fit_bundles(self, profiles: tuple[str, ...]) -> dict[str, object]: ...

    def final_confirmation(
        self,
        *,
        sealed_test_token: str | None,
        fitted_pipelines: dict[str, object] | None = None,
    ) -> BenchmarkResult: ...
