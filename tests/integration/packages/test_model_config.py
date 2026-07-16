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
    catalog = load_model_profiles(Path("configs/model/profiles.yaml"))

    assert catalog.random_seed == 42
    assert [
        (item.name, item.kind.value, item.threshold) for item in catalog.profiles
    ] == [
        ("baseline", "logistic_regression", 0.50),
        ("candidate-a", "random_forest", 0.40),
        ("candidate-b", "random_forest", 0.35),
    ]


def test_evaluation_plan_preserves_repeated_cv_and_bootstrap() -> None:
    plan = load_evaluation_plan(Path("configs/model/evaluation.yaml"))

    assert (plan.cv_splits, plan.cv_repeats) == (5, 3)
    assert plan.bootstrap_iterations == 1000
    assert plan.cross_validation_metric_names == (
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "pr_auc",
    )
