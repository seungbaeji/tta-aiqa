"""Sklearn fitting for frozen train and valid model data."""

from collections.abc import Callable

import pandas as pd
from sklearn.pipeline import Pipeline

from aiqa_model.domain import ModelProfile
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
