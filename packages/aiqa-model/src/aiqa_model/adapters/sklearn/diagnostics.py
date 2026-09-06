"""Sklearn feature diagnostics derived from train and valid data only."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
from aiqa_core.domain import FeatureSet
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

from aiqa_model.adapters.sklearn.selection import select_profile
from aiqa_model.domain import (
    DEVELOPMENT_DATASET_ROLES,
    FeatureCoefficient,
    FeatureDiagnostics,
    FeatureDiagnosticsRequest,
    FeatureSelection,
    FeatureSummary,
    ModelProfile,
    PermutationImportance,
)


class SklearnFeatureDiagnostician:
    """Generate configured feature diagnostics using sklearn estimators."""

    def __init__(
        self,
        feature_set: FeatureSet,
        random_seed: int,
        pipeline_builder: Callable[[ModelProfile], Pipeline],
    ) -> None:
        self._feature_set = feature_set
        self._random_seed = random_seed
        self._pipeline_builder = pipeline_builder

    def produce(
        self,
        *,
        request: FeatureDiagnosticsRequest,
        profiles: tuple[ModelProfile, ...],
        train: pd.DataFrame,
        valid: pd.DataFrame,
    ) -> FeatureDiagnostics:
        """Compare configured profiles without accessing the sealed test role."""
        feature_names = list(self._feature_set.feature_names)
        baseline = self._pipeline_builder(
            select_profile(profiles, request.baseline_profile)
        )
        baseline.fit(train[feature_names], train["target"])
        transformed_names = baseline.named_steps["preprocessor"].get_feature_names_out()
        coefficients = baseline.named_steps["model"].coef_[0]

        candidate = self._pipeline_builder(
            select_profile(profiles, request.candidate_profile)
        )
        candidate.fit(train[feature_names], train["target"])
        permutation = permutation_importance(
            candidate,
            valid[feature_names],
            valid["target"],
            scoring="average_precision",
            n_repeats=5,
            random_state=self._random_seed,
            n_jobs=1,
        )

        summaries = tuple(
            summarize_feature(train, feature.name, feature.dtype.value)
            for feature in self._feature_set.features
        )
        coefficients_by_feature = tuple(
            FeatureCoefficient(feature=str(name), coefficient=float(value))
            for name, value in sorted(
                zip(transformed_names, coefficients, strict=True),
                key=lambda item: abs(item[1]),
                reverse=True,
            )[:25]
        )
        permutation_by_feature = tuple(
            PermutationImportance(
                feature=name,
                mean=float(mean),
                standard_deviation=float(standard_deviation),
            )
            for name, mean, standard_deviation in sorted(
                zip(
                    feature_names,
                    permutation.importances_mean,
                    permutation.importances_std,
                    strict=True,
                ),
                key=lambda item: item[1],
                reverse=True,
            )
        )
        return FeatureDiagnostics(
            schema_version=1,
            accessed_roles=DEVELOPMENT_DATASET_ROLES,
            test_accessed=False,
            feature_count=len(feature_names),
            selection=FeatureSelection.RETAIN_ALL_CANONICAL,
            features=summaries,
            top_baseline_coefficients=coefficients_by_feature,
            candidate_permutation_importance=permutation_by_feature,
        )


def summarize_feature(
    frame: pd.DataFrame, feature_name: str, dtype: str
) -> FeatureSummary:
    """Summarize one canonical model input against the development target."""
    series = frame[feature_name]
    numeric = pd.to_numeric(series, errors="coerce")
    variance = float(numeric.var(ddof=0)) if numeric.notna().any() else None
    correlation = None
    if numeric.notna().sum() > 1 and numeric.nunique(dropna=True) > 1:
        correlation = float(numeric.corr(frame["target"].astype(float)))
    return FeatureSummary(
        feature=feature_name,
        dtype=dtype,
        missing_rate=float(series.isna().mean()),
        distinct_values=int(series.nunique(dropna=True)),
        variance=variance,
        target_correlation=correlation,
    )
