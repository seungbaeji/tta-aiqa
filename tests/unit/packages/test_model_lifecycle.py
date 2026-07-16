"""Framework-independent model lifecycle use case tests."""

from dataclasses import dataclass

import pytest
from aiqa_model.application import (
    confirm_frozen_models,
    develop_models,
    diagnose_features,
    fit_model_bundles,
)
from aiqa_model.domain import (
    SEALED_TEST_CONFIRMATION_TOKEN,
    BenchmarkResult,
    BinaryMetrics,
    FeatureDiagnostics,
    FeatureDiagnosticsRequest,
    FeatureSelection,
    FeatureSummary,
    ModelProfileSelection,
    ProfileEvaluation,
    SealedTestConfirmation,
)
from aiqa_model.ports import FittedModels


def result(
    profile_names: tuple[str, ...], role: str = "valid"
) -> BenchmarkResult:
    return BenchmarkResult(
        evaluation_role=role,
        accessed_roles=("train", "valid")
        if role == "valid"
        else ("train", "valid", "test"),
        profiles=tuple(profile_evaluation(name) for name in profile_names),
    )


@dataclass
class DevelopmentEvaluator:
    seen: ModelProfileSelection | None = None

    def evaluate_development(self, selection: ModelProfileSelection) -> BenchmarkResult:
        self.seen = selection
        return result(selection.names)


@dataclass
class Diagnostician:
    seen: FeatureDiagnosticsRequest | None = None

    def produce_feature_diagnostics(
        self, request: FeatureDiagnosticsRequest
    ) -> FeatureDiagnostics:
        self.seen = request
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


@dataclass
class ModelFitter:
    seen: ModelProfileSelection | None = None

    def fit_models(self, selection: ModelProfileSelection) -> FittedModels:
        self.seen = selection
        return FittedModels.from_mapping(
            {profile: object() for profile in selection.names}
        )


@dataclass
class FrozenEvaluator:
    seen: tuple[ModelProfileSelection, FittedModels] | None = None

    def evaluate_frozen_models(
        self,
        selection: ModelProfileSelection,
        fitted_models: FittedModels,
    ) -> BenchmarkResult:
        self.seen = (selection, fitted_models)
        return result(selection.names, "test")


def profile_evaluation(name: str) -> ProfileEvaluation:
    """Create a minimal valid profile result for an application boundary fake."""
    return ProfileEvaluation(
        profile=name,
        threshold=0.5,
        metrics=BinaryMetrics(0.5, 0.5, 0.5, 0.6, 0.4, 1, 1, 1, 1),
        bootstrap_recall_lower=0.2,
        cross_validation=(),
    )


def test_lifecycle_use_cases_preserve_the_requested_profile_selection() -> None:
    selection = ModelProfileSelection.from_names(("candidate-b", "baseline"))
    development = DevelopmentEvaluator()
    fitter = ModelFitter()
    frozen = FrozenEvaluator()

    developed = develop_models(selection=selection, evaluator=development)
    fitted = fit_model_bundles(selection=selection, fitter=fitter)
    confirmed = confirm_frozen_models(
        confirmation=SealedTestConfirmation(SEALED_TEST_CONFIRMATION_TOKEN),
        selection=selection,
        evaluator=frozen,
        fitted_models=fitted,
    )

    assert developed.evaluation_role == "valid"
    assert development.seen == selection
    assert fitter.seen == selection
    assert frozen.seen == (selection, fitted)
    assert confirmed.evaluation_role == "test"


def test_feature_diagnostics_use_case_passes_a_typed_comparison_request() -> None:
    request = FeatureDiagnosticsRequest(
        baseline_profile="baseline", candidate_profile="candidate-b"
    )
    diagnostician = Diagnostician()

    diagnostics = diagnose_features(request=request, diagnostician=diagnostician)

    assert diagnostics.selection is FeatureSelection.RETAIN_ALL_CANONICAL
    assert diagnostician.seen == request


def test_sealed_confirmation_rejects_an_unacknowledged_token() -> None:
    with pytest.raises(PermissionError, match="explicit confirmation token"):
        SealedTestConfirmation("not-confirmed")


def test_confirmation_rejects_a_model_set_other_than_the_frozen_selection() -> None:
    selection = ModelProfileSelection.from_names(("baseline", "candidate-b"))
    frozen = FrozenEvaluator()

    with pytest.raises(ValueError, match="sealed-test selection"):
        confirm_frozen_models(
            confirmation=SealedTestConfirmation(SEALED_TEST_CONFIRMATION_TOKEN),
            selection=selection,
            evaluator=frozen,
            fitted_models=FittedModels.from_mapping({"baseline": object()}),
        )

    assert frozen.seen is None


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


def test_profile_selection_rejects_duplicate_or_untrimmed_names() -> None:
    with pytest.raises(ValueError, match="unique"):
        ModelProfileSelection(("baseline", "baseline"))
    with pytest.raises(ValueError, match="trimmed"):
        ModelProfileSelection((" baseline",))


def test_benchmark_result_rejects_roles_that_do_not_match_its_stage() -> None:
    with pytest.raises(ValueError, match="role access"):
        BenchmarkResult(
            evaluation_role="test",
            accessed_roles=("test",),
            profiles=(profile_evaluation("baseline"),),
        )
