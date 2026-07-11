"""Framework-independent model lifecycle use case tests."""

from dataclasses import dataclass, field

from aiqa_model.application import (
    ConfirmFrozenModels,
    DevelopModels,
    DiagnoseFeatures,
    FitModelBundles,
)
from aiqa_model.domain import BenchmarkResult, BinaryMetrics, ProfileEvaluation


def result(role: str = "valid") -> BenchmarkResult:
    return BenchmarkResult(
        evaluation_role=role,
        accessed_roles=("train", "valid") if role == "valid" else ("test",),
        profiles=(
            ProfileEvaluation(
                profile="baseline",
                threshold=0.5,
                metrics=BinaryMetrics(0.5, 0.5, 0.5, 0.6, 0.4, 1, 1, 1, 1),
                bootstrap_recall_lower=0.2,
                cross_validation=(),
            ),
        ),
    )


@dataclass
class FakeBenchmark:
    calls: list[object] = field(default_factory=list)

    def development(self) -> BenchmarkResult:
        self.calls.append("development")
        return result()

    def feature_diagnostics(
        self, *, baseline_profile: str, candidate_profile: str
    ) -> dict[str, object]:
        self.calls.append((baseline_profile, candidate_profile))
        return {"selection": "retain_all"}

    def fit_bundles(self, profiles: tuple[str, ...]) -> dict[str, object]:
        self.calls.append(profiles)
        return {profile: object() for profile in profiles}

    def final_confirmation(
        self,
        *,
        sealed_test_token: str | None,
        fitted_pipelines: dict[str, object] | None = None,
    ) -> BenchmarkResult:
        self.calls.append((sealed_test_token, fitted_pipelines))
        return result("test")


def test_lifecycle_use_cases_drive_benchmark_only_through_port() -> None:
    benchmark = FakeBenchmark()

    assert DevelopModels(benchmark).execute().evaluation_role == "valid"
    assert DiagnoseFeatures(benchmark).execute(
        baseline_profile="baseline", candidate_profile="candidate-b"
    ) == {"selection": "retain_all"}
    fitted = FitModelBundles(benchmark).execute(("baseline", "candidate-b"))
    confirmed = ConfirmFrozenModels(benchmark).execute(
        sealed_test_token="token", fitted_models=fitted
    )

    assert confirmed.evaluation_role == "test"
    assert benchmark.calls == [
        "development",
        ("baseline", "candidate-b"),
        ("baseline", "candidate-b"),
        ("token", fitted),
    ]
