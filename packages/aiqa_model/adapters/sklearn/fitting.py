"""Sklearn fitting for frozen train and valid model data."""

from collections.abc import Callable
from warnings import catch_warnings, simplefilter

import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.pipeline import Pipeline

from aiqa_model.adapters.sklearn.evaluation import binary_metrics
from aiqa_model.domain import MetricAtStep, ModelKind, ModelProfile
from aiqa_model.ports import FittedModels


def fit_profiles(
    *,
    profiles: tuple[ModelProfile, ...],
    frame: pd.DataFrame,
    feature_names: tuple[str, ...],
    pipeline_builder: Callable[[ModelProfile], Pipeline],
) -> FittedModels:
    """Fit each selected profile and return deterministic opaque model artifacts."""
    features = frame[list(feature_names)]
    target = frame["target"].to_numpy(dtype=int)
    models: dict[str, object] = {}
    for profile in profiles:
        pipeline = pipeline_builder(profile)
        pipeline.fit(features, target)
        models[profile.name] = pipeline
    return FittedModels.from_mapping(models)


def fit_pipeline_with_history(
    *,
    pipeline: Pipeline,
    profile: ModelProfile,
    train: pd.DataFrame,
    valid: pd.DataFrame,
    feature_names: tuple[str, ...],
) -> tuple[Pipeline, tuple[MetricAtStep, ...]]:
    """Fit one pipeline and record valid metrics at each iterative training step."""
    train_features = train[list(feature_names)]
    train_target = train["target"].to_numpy(dtype=int)
    if profile.kind is not ModelKind.MLP_CLASSIFIER:
        pipeline.fit(train_features, train_target)
        return pipeline, ()
    return _fit_mlp_with_history(
        pipeline=pipeline,
        profile=profile,
        train_features=train_features,
        train_target=train_target,
        valid=valid,
        feature_names=feature_names,
    )


def _fit_mlp_with_history(
    *,
    pipeline: Pipeline,
    profile: ModelProfile,
    train_features: pd.DataFrame,
    train_target: object,
    valid: pd.DataFrame,
    feature_names: tuple[str, ...],
) -> tuple[Pipeline, tuple[MetricAtStep, ...]]:
    """Advance sklearn MLP one iteration at a time and score the course valid split."""
    max_iter = int(profile.parameter_dict()["max_iter"])
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    transformed_train = preprocessor.fit_transform(train_features)
    transformed_valid = preprocessor.transform(valid[list(feature_names)])
    valid_target = valid["target"].to_numpy(dtype=int)
    history: list[MetricAtStep] = []
    model.set_params(warm_start=True)
    with catch_warnings():
        simplefilter("ignore", ConvergenceWarning)
        for step in range(1, max_iter + 1):
            model.set_params(max_iter=step)
            model.fit(transformed_train, train_target)
            probabilities = model.predict_proba(transformed_valid)[:, 1]
            metrics = binary_metrics(valid_target, probabilities, profile.threshold)
            history.extend(
                (
                    MetricAtStep(
                        "train.loss", float(model.loss_curve_[-1]), step
                    ),
                    MetricAtStep("valid.precision", metrics.precision, step),
                    MetricAtStep("valid.recall", metrics.recall, step),
                    MetricAtStep("valid.f1", metrics.f1, step),
                    MetricAtStep("valid.roc_auc", metrics.roc_auc, step),
                    MetricAtStep("valid.pr_auc", metrics.pr_auc, step),
                )
            )
    model.set_params(warm_start=False, max_iter=max_iter)
    return pipeline, tuple(history)
