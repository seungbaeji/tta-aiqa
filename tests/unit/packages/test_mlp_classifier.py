"""sklearn MLPClassifier is an iterative student-development model family."""

from pathlib import Path

import pandas as pd
import pytest
from aiqa_core.domain import FeatureDefinition, FeatureSet, FeatureType
from aiqa_model.adapters.mlflow.model import MlflowModelTracker
from aiqa_model.adapters.sklearn.fitting import fit_pipeline_with_history
from aiqa_model.adapters.sklearn.pipeline import (
    build_estimator,
    build_model_pipeline,
)
from aiqa_model.domain import (
    BinaryMetrics,
    MetricAtStep,
    ModelKind,
    ModelProfile,
    ModelRole,
    ProfileEvaluation,
)
from mlflow import MlflowClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier


def mlp_profile(max_iter: int = 3) -> ModelProfile:
    return ModelProfile(
        name="candidate-c",
        model_role=ModelRole.CANDIDATE,
        candidate_id="candidate-c",
        kind=ModelKind.MLP_CLASSIFIER,
        threshold=0.35,
        params=(
            ("activation", "relu"),
            ("alpha", 0.0001),
            ("batch_size", 16),
            ("early_stopping", False),
            ("hidden_layer_sizes", (8, 4)),
            ("learning_rate_init", 0.01),
            ("max_iter", max_iter),
            ("solver", "adam"),
        ),
    )


def forest_profile() -> ModelProfile:
    return ModelProfile(
        name="candidate-b",
        model_role=ModelRole.CANDIDATE,
        candidate_id="candidate-b",
        kind=ModelKind.RANDOM_FOREST,
        threshold=0.35,
        params=(("n_estimators", 8), ("n_jobs", 1)),
    )


def feature_set() -> FeatureSet:
    return FeatureSet(
        schema_version=1,
        name="test-features",
        target="target",
        features=(FeatureDefinition("feat", FeatureType.FLOAT, False),),
    )


def toy_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    train = pd.DataFrame(
        {
            "feat": [0.1, 0.2, 0.15, 0.8, 0.85, 0.9],
            "target": [0, 0, 0, 1, 1, 1],
        }
    )
    valid = pd.DataFrame({"feat": [0.12, 0.88], "target": [0, 1]})
    return train, valid


def test_metric_at_step_rejects_zero_based_iterations() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        MetricAtStep("train.loss", 0.5, 0)


def test_mlp_estimator_uses_configured_hidden_layers() -> None:
    estimator = build_estimator(mlp_profile(), random_seed=43)

    assert isinstance(estimator, MLPClassifier)
    assert estimator.hidden_layer_sizes == (8, 4)
    assert estimator.max_iter == 3
    assert estimator.early_stopping is False


def test_mlp_rejects_sklearn_early_stopping() -> None:
    profile = ModelProfile(
        name="candidate-c",
        model_role=ModelRole.CANDIDATE,
        candidate_id="candidate-c",
        kind=ModelKind.MLP_CLASSIFIER,
        threshold=0.35,
        params=(
            ("early_stopping", True),
            ("hidden_layer_sizes", (4,)),
            ("max_iter", 2),
        ),
    )

    with pytest.raises(ValueError, match="early_stopping"):
        build_estimator(profile, random_seed=43)


def test_random_forest_fit_does_not_emit_iteration_history() -> None:
    train, valid = toy_frames()
    pipeline = build_model_pipeline(
        feature_set=feature_set(),
        profile=forest_profile(),
        random_seed=43,
    )

    fitted, history = fit_pipeline_with_history(
        pipeline=pipeline,
        profile=forest_profile(),
        train=train,
        valid=valid,
        feature_names=("feat",),
    )

    assert isinstance(fitted.named_steps["model"], RandomForestClassifier)
    assert history == ()


def test_mlp_fit_records_one_valid_metric_point_per_iteration() -> None:
    train, valid = toy_frames()
    pipeline = build_model_pipeline(
        feature_set=feature_set(),
        profile=mlp_profile(max_iter=4),
        random_seed=43,
    )

    fitted, history = fit_pipeline_with_history(
        pipeline=pipeline,
        profile=mlp_profile(max_iter=4),
        train=train,
        valid=valid,
        feature_names=("feat",),
    )

    steps = tuple(item.step for item in history if item.name == "train.loss")
    names = {item.name for item in history}

    assert isinstance(fitted.named_steps["model"], MLPClassifier)
    assert steps == (1, 2, 3, 4)
    assert names == {
        "train.loss",
        "valid.precision",
        "valid.recall",
        "valid.f1",
        "valid.roc_auc",
        "valid.pr_auc",
    }


@pytest.mark.integration
def test_mlflow_records_mlp_metrics_against_training_steps(tmp_path: Path) -> None:
    train, valid = toy_frames()
    train_path = tmp_path / "train.csv"
    valid_path = tmp_path / "valid.csv"
    train.assign(record_id=[1, 2, 3, 4, 5, 6]).to_csv(train_path, index=False)
    valid.assign(record_id=[7, 8]).to_csv(valid_path, index=False)
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "metadata.json").write_text("{}\n", encoding="utf-8")
    pipeline = build_model_pipeline(
        feature_set=feature_set(),
        profile=mlp_profile(max_iter=3),
        random_seed=43,
    )
    fitted, history = fit_pipeline_with_history(
        pipeline=pipeline,
        profile=mlp_profile(max_iter=3),
        train=train,
        valid=valid,
        feature_names=("feat",),
    )
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    evaluation = ProfileEvaluation(
        profile="candidate-c",
        threshold=0.35,
        metrics=BinaryMetrics(0.5, 0.5, 0.5, 0.5, 0.5, 1, 0, 0, 1),
        bootstrap_recall_lower=0.1,
        cross_validation=(),
    )

    run_id = MlflowModelTracker(
        tracking_uri,
        "student-mlp-history",
        tmp_path / "mlruns",
    ).record(
        profile=mlp_profile(max_iter=3),
        evaluation=evaluation,
        pipeline=fitted,
        bundle_dir=bundle_dir,
        train_path=train_path,
        valid_path=valid_path,
        provenance={"train_data_hash": "a" * 64, "valid_data_hash": "b" * 64},
        metric_history=history,
    )

    client = MlflowClient(tracking_uri=tracking_uri)
    loss_history = client.get_metric_history(run_id, "train.loss")
    auc_history = client.get_metric_history(run_id, "valid.roc_auc")
    run = client.get_run(run_id)

    assert [item.step for item in loss_history] == [1, 2, 3]
    assert [item.step for item in auc_history] == [1, 2, 3]
    assert run.data.params["model_kind"] == "mlp_classifier"
    assert run.data.params["model.hidden_layer_sizes"] == "(8, 4)"
    assert "valid.false_negative" in run.data.metrics
