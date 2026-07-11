"""Scikit-learn classifier adapter used by chapter 2 labs."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from ai_quality.common.labels import POSITIVE_LABEL


def build_training_frame(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
) -> pd.DataFrame:
    """Return rows with valid labels for model training or evaluation."""
    columns = [*feature_columns, target_column]
    return dataframe.loc[:, columns].dropna(subset=[target_column]).copy()


def train_sklearn_classifier(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
) -> Pipeline:
    """Train a tree-based binary classifier for the course labs."""
    training_frame = build_training_frame(dataframe, feature_columns, target_column)
    features = training_frame.loc[:, feature_columns]
    labels = (training_frame[target_column] == POSITIVE_LABEL).astype(int)

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=6,
                    min_samples_leaf=20,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ]
    )
    model.fit(features, labels)
    return model


def predict_positive_scores(
    model: Any,
    dataframe: pd.DataFrame,
    feature_columns: list[str],
) -> list[float]:
    """Return positive-class scores from a fitted classifier."""
    probabilities = model.predict_proba(dataframe.loc[:, feature_columns])
    return [float(value) for value in probabilities[:, 1]]


def save_model(model: Any, output_path: Path) -> Path:
    """Persist a fitted model artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as file:
        pickle.dump(model, file)
    return output_path


def load_model(model_path: Path) -> Any:
    """Load a fitted model artifact."""
    with model_path.open("rb") as file:
        return pickle.load(file)
