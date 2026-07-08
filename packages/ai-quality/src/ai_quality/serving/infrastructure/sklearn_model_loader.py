"""Sklearn model loader for serving."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ai_quality.model_quality.infrastructure.sklearn_classifier import load_model


@dataclass(frozen=True)
class SklearnScoringModel:
    """Score feature dictionaries with a fitted sklearn classifier."""

    model: Any
    feature_columns: tuple[str, ...]

    def score_one(self, features: dict[str, float]) -> float:
        """Return one positive-class score."""
        dataframe = pd.DataFrame(
            [{column: features[column] for column in self.feature_columns}]
        )
        probabilities = self.model.predict_proba(
            dataframe.loc[:, list(self.feature_columns)]
        )
        return float(probabilities[0, 1])


def load_sklearn_scoring_model(
    model_path: Path,
    feature_columns: tuple[str, ...],
) -> SklearnScoringModel:
    """Load an sklearn model artifact for serving."""
    return SklearnScoringModel(
        model=load_model(model_path),
        feature_columns=feature_columns,
    )
