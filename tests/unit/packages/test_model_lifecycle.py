"""Framework-independent model lifecycle use case tests."""

from dataclasses import dataclass, field

import pytest
from aiqa_model.application import (
    ConfirmFrozenModels,
    DevelopModels,
    DiagnoseFeatures,
    FitModelBundles,
)
from aiqa_model.domain import (
    BenchmarkResult,
    BinaryMetrics,
    FeatureDiagnostics,
    FeatureSelection,
    FeatureSummary,
    ProfileEvaluation,
)
from aiqa_model.ports import FittedModels


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
    ) -> FeatureDiagnostics:
        self.calls.append((baseline_profile, candidate_profile))
        return FeatureDiagnostics(
            schema_version=1,
            accessed_roles=("train", "valid"),
            test_accessed=False,
            feature_count=1,
            selection=FeatureSelection.RETAIN_ALL_CANONICAL,
            features=(FeatureSummary("value", "float", 0.0, 2, 0.25, 0.5),),
            top_baseline_coefficients=(),
            candidate_permutation_importance=(),
        )

    def fit_bundles(self, profiles: tuple[str, ...]) -> FittedModels:
        self.calls.append(profiles)
        return FittedModels(tuple((profile, object()) for profile in profiles))

    def final_confirmation(
        self,
        *,
        sealed_test_token: str | None,
        fitted_pipelines: FittedModels | None = None,
    ) -> BenchmarkResult:
        self.calls.append((sealed_test_token, fitted_pipelines))
        return result("test")


def test_lifecycle_use_cases_drive_benchmark_only_through_port() -> None:
    benchmark = FakeBenchmark()

    assert DevelopModels(benchmark).execute().evaluation_role == "valid"
    diagnostics = DiagnoseFeatures(benchmark).execute(
        baseline_profile="baseline", candidate_profile="candidate-b"
    )
    assert diagnostics.selection is FeatureSelection.RETAIN_ALL_CANONICAL
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


def test_fitted_models_are_named_and_deterministic() -> None:
    first = object()
    second = object()

    models = FittedModels.from_mapping({"candidate-b": second, "baseline": first})

    assert models.names == ("baseline", "candidate-b")
    assert models.get("baseline") is first
    with pytest.raises(KeyError, match="does not exist"):
        models.get("candidate-a")


def test_fitted_models_reject_duplicate_names() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        FittedModels((("baseline", object()), ("baseline", object())))


def test_fitted_models_reject_unsorted_names() -> None:
    with pytest.raises(ValueError, match="must be sorted"):
        FittedModels((("candidate-b", object()), ("baseline", object())))
