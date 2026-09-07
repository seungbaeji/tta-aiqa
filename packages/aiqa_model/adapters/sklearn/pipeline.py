"""Sklearn preprocessing and estimator construction."""

from __future__ import annotations

from typing import Any

from aiqa_core.domain import FeatureSet, FeatureType
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from aiqa_model.domain import ModelKind, ModelProfile


def build_model_pipeline(
    *,
    feature_set: FeatureSet,
    profile: ModelProfile,
    random_seed: int,
) -> Pipeline:
    """Build an unfitted sklearn pipeline for one immutable model profile."""
    return Pipeline(
        [
            ("preprocessor", build_preprocessor(feature_set)),
            ("model", build_estimator(profile, random_seed)),
        ]
    )


def build_preprocessor(feature_set: FeatureSet) -> ColumnTransformer:
    """Build preprocessing that preserves the canonical feature contract order."""
    categorical_features = [
        feature.name
        for feature in feature_set.features
        if feature.dtype is FeatureType.CATEGORY
    ]
    numeric_features = [
        feature.name
        for feature in feature_set.features
        if feature.dtype is not FeatureType.CATEGORY
    ]
    return ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="median", add_indicator=True),
                        ),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(
                                handle_unknown="ignore", sparse_output=True
                            ),
                        ),
                    ]
                ),
                categorical_features,
            ),
        ]
    )


def build_estimator(profile: ModelProfile, random_seed: int) -> object:
    """Build the sklearn estimator selected by a versioned model profile."""
    params: dict[str, Any] = profile.parameter_dict()
    if profile.kind is ModelKind.LOGISTIC_REGRESSION:
        return LogisticRegression(random_state=random_seed, **params)
    if profile.kind is ModelKind.RANDOM_FOREST:
        return RandomForestClassifier(random_state=random_seed, **params)
    raise ValueError(f"unsupported model kind: {profile.kind}")
