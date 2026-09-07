"""Frozen model and feature configuration tests."""

from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_model.adapters import load_evaluation_plan, load_model_profiles


def test_canonical_contract_uses_all_133_available_features() -> None:
    feature_set = load_feature_contract(Path("configs/contracts/model-input.yaml"))

    assert len(feature_set.features) == 133
    assert sum(item.dtype.value == "boolean" for item in feature_set.features) == 25
    assert feature_set.feature_names[0:4] == (
        "age",
        "age__missing",
        "gender",
        "gender__missing",
    )


def test_three_profiles_are_frozen_to_phase0_operating_points() -> None:
    catalog = load_model_profiles(Path("configs/model-v1/profiles.yaml"))

    assert catalog.random_seed == 42
    assert [
        (item.name, item.kind.value, item.threshold) for item in catalog.profiles
    ] == [
        ("baseline", "logistic_regression", 0.50),
        ("candidate-a", "random_forest", 0.40),
        ("candidate-b", "random_forest", 0.35),
    ]


def test_v2_official_catalog_stays_three_frozen_profiles() -> None:
    catalog = load_model_profiles(Path("configs/model-v2/profiles.yaml"))

    assert catalog.random_seed == 43
    assert [
        (item.name, item.kind.value, item.threshold) for item in catalog.profiles
    ] == [
        ("baseline", "logistic_regression", 0.50),
        ("candidate-a", "random_forest", 0.40),
        ("candidate-b", "random_forest", 0.35),
    ]


def test_student_development_catalog_owns_the_mlp_classifier() -> None:
    catalog = load_model_profiles(Path("configs/model-v2/student-profiles.yaml"))

    assert catalog.random_seed == 43
    assert [item.name for item in catalog.profiles] == ["candidate-c"]
    profile = catalog.profiles[0]
    assert profile.kind.value == "mlp_classifier"
    assert profile.threshold == 0.35
    assert profile.parameter_dict()["hidden_layer_sizes"] == (32, 16)
    assert profile.parameter_dict()["max_iter"] == 30
    assert profile.parameter_dict()["early_stopping"] is False


def test_evaluation_plan_preserves_repeated_cv_and_bootstrap() -> None:
    plan = load_evaluation_plan(Path("configs/model-v1/evaluation.yaml"))

    assert (plan.cv_splits, plan.cv_repeats) == (5, 3)
    assert plan.bootstrap_iterations == 1000
    assert plan.cross_validation_metric_names == (
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "pr_auc",
    )
