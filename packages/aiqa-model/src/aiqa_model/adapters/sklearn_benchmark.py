"""Sklearn benchmark adapter with explicit sealed-role access."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from aiqa_core.domain import FeatureSet, FeatureType
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from aiqa_model.domain import (
    BenchmarkResult,
    BinaryMetrics,
    EvaluationPlan,
    FeatureCoefficient,
    FeatureDiagnostics,
    FeatureSelection,
    FeatureSummary,
    MetricDistribution,
    ModelKind,
    ModelProfile,
    PermutationImportance,
    ProfileEvaluation,
)
from aiqa_model.ports import FittedModels


class SklearnBenchmark:
    """Evaluate configured sklearn profiles while enforcing dataset-role access."""

    def __init__(
        self,
        dataset_dir: Path,
        feature_set: FeatureSet,
        profiles: tuple[ModelProfile, ...],
        evaluation_plan: EvaluationPlan,
        random_seed: int,
    ) -> None:
        self._dataset_dir = dataset_dir
        self._feature_set = feature_set
        self._profiles = profiles
        self._plan = evaluation_plan
        self._random_seed = random_seed

    def development(self) -> BenchmarkResult:
        """Fit and evaluate every profile using train and valid roles."""
        train = self._read_role("train")
        valid = self._read_role("valid")
        evaluations = tuple(
            self._evaluate_profile(profile, train, valid, include_cv=True)
            for profile in self._profiles
        )
        return BenchmarkResult(
            evaluation_role="valid",
            accessed_roles=("train", "valid"),
            profiles=evaluations,
        )

    def final_confirmation(
        self,
        *,
        sealed_test_token: str | None,
        fitted_pipelines: FittedModels | None = None,
    ) -> BenchmarkResult:
        """Evaluate frozen pipelines against test after explicit confirmation."""
        if sealed_test_token != "CONFIRM-FROZEN-CANONICAL-TEST":
            raise PermissionError("sealed test requires an explicit confirmation token")
        test = self._read_role("test", allow_sealed=True)
        if fitted_pipelines is None:
            fit = pd.concat(
                [self._read_role("train"), self._read_role("valid")],
                ignore_index=True,
            )
            evaluations = tuple(
                self._evaluate_profile(profile, fit, test, include_cv=False)
                for profile in self._profiles
            )
        else:
            expected = tuple(sorted(profile.name for profile in self._profiles))
            if fitted_pipelines.names != expected:
                raise ValueError(
                    "fitted pipeline profiles do not match benchmark profiles"
                )
            evaluations = tuple(
                self._evaluate_fitted_profile(
                    profile, fitted_pipelines.get(profile.name), test
                )
                for profile in self._profiles
            )
        return BenchmarkResult(
            evaluation_role="test",
            accessed_roles=("train", "valid", "test"),
            profiles=evaluations,
        )

    def fit_bundles(self, profiles: tuple[str, ...]) -> FittedModels:
        """Fit requested profiles on train and valid and return named bundles."""
        fit = pd.concat(
            [self._read_role("train"), self._read_role("valid")],
            ignore_index=True,
        )
        x = fit[list(self._feature_set.feature_names)]
        y = fit["target"].to_numpy(dtype=int)
        bundles: dict[str, Pipeline] = {}
        for profile in self._profiles:
            if profile.name not in profiles:
                continue
            pipeline = self._pipeline(profile)
            pipeline.fit(x, y)
            bundles[profile.name] = pipeline
        missing = set(profiles) - set(bundles)
        if missing:
            raise ValueError(f"unknown model profiles requested: {sorted(missing)}")
        return FittedModels.from_mapping(bundles)

    def feature_diagnostics(
        self, *, baseline_profile: str, candidate_profile: str
    ) -> FeatureDiagnostics:
        """Compare feature behavior for two profiles using train and valid only."""
        train = self._read_role("train")
        valid = self._read_role("valid")
        names = list(self._feature_set.feature_names)
        profiles = {profile.name: profile for profile in self._profiles}

        baseline = self._pipeline(profiles[baseline_profile])
        baseline.fit(train[names], train["target"])
        transformed_names = baseline.named_steps["preprocessor"].get_feature_names_out()
        coefficients = baseline.named_steps["model"].coef_[0]

        candidate = self._pipeline(profiles[candidate_profile])
        candidate.fit(train[names], train["target"])
        permutation = permutation_importance(
            candidate,
            valid[names],
            valid["target"],
            scoring="average_precision",
            n_repeats=5,
            random_state=self._random_seed,
            n_jobs=1,
        )

        diagnostics: list[FeatureSummary] = []
        target = train["target"].astype(float)
        for feature in self._feature_set.features:
            series = train[feature.name]
            numeric = pd.to_numeric(series, errors="coerce")
            variance = float(numeric.var(ddof=0)) if numeric.notna().any() else None
            correlation = None
            if numeric.notna().sum() > 1 and numeric.nunique(dropna=True) > 1:
                correlation = float(numeric.corr(target))
            diagnostics.append(
                FeatureSummary(
                    feature=feature.name,
                    dtype=feature.dtype.value,
                    missing_rate=float(series.isna().mean()),
                    distinct_values=int(series.nunique(dropna=True)),
                    variance=variance,
                    target_correlation=correlation,
                )
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
                standard_deviation=float(std),
            )
            for name, mean, std in sorted(
                    zip(
                        names,
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
            accessed_roles=("train", "valid"),
            test_accessed=False,
            feature_count=len(names),
            selection=FeatureSelection.RETAIN_ALL_CANONICAL,
            features=tuple(diagnostics),
            top_baseline_coefficients=coefficients_by_feature,
            candidate_permutation_importance=permutation_by_feature,
        )

    def _read_role(self, role: str, *, allow_sealed: bool = False) -> pd.DataFrame:
        if role in {"test", "operational"} and not allow_sealed:
            raise PermissionError(f"sealed dataset role requested: {role}")
        frame = pd.read_csv(self._dataset_dir / f"{role}.csv")
        expected = set(self._feature_set.feature_names)
        actual = set(frame.columns) - {"record_id", "target"}
        if actual != expected:
            raise ValueError(
                f"model input contract mismatch: missing={sorted(expected - actual)}, "
                f"extra={sorted(actual - expected)}"
            )
        if "record_id" in expected or self._feature_set.target in expected:
            raise ValueError("identifier or target leaked into model input contract")
        if role != "operational" and "target" not in frame:
            raise ValueError(f"target missing from model dataset role: {role}")
        if role == "operational" and "target" in frame:
            raise ValueError("operational traffic pool must not contain target")
        return frame

    def _evaluate_profile(
        self,
        profile: ModelProfile,
        fit: pd.DataFrame,
        score: pd.DataFrame,
        *,
        include_cv: bool,
    ) -> ProfileEvaluation:
        names = list(self._feature_set.feature_names)
        x_fit = fit[names]
        y_fit = fit["target"].to_numpy(dtype=int)
        pipeline = self._pipeline(profile)
        pipeline.fit(x_fit, y_fit)
        probabilities = pipeline.predict_proba(score[names])[:, 1]
        target = score["target"].to_numpy(dtype=int)
        metrics = binary_metrics(target, probabilities, profile.threshold)
        recall_lower = bootstrap_recall_lower(
            target,
            probabilities,
            profile.threshold,
            iterations=self._plan.bootstrap_iterations,
            confidence_level=self._plan.confidence_level,
            random_seed=self._random_seed,
        )
        cv = self._cross_validate(profile, fit) if include_cv else ()
        return ProfileEvaluation(
            profile=profile.name,
            threshold=profile.threshold,
            metrics=metrics,
            bootstrap_recall_lower=recall_lower,
            cross_validation=cv,
        )

    def _evaluate_fitted_profile(
        self,
        profile: ModelProfile,
        pipeline: Pipeline,
        score: pd.DataFrame,
    ) -> ProfileEvaluation:
        names = list(self._feature_set.feature_names)
        probabilities = pipeline.predict_proba(score[names])[:, 1]
        target = score["target"].to_numpy(dtype=int)
        metrics = binary_metrics(target, probabilities, profile.threshold)
        return ProfileEvaluation(
            profile=profile.name,
            threshold=profile.threshold,
            metrics=metrics,
            bootstrap_recall_lower=bootstrap_recall_lower(
                target,
                probabilities,
                profile.threshold,
                iterations=self._plan.bootstrap_iterations,
                confidence_level=self._plan.confidence_level,
                random_seed=self._random_seed,
            ),
            cross_validation=(),
        )

    def _cross_validate(
        self, profile: ModelProfile, train: pd.DataFrame
    ) -> tuple[tuple[str, MetricDistribution], ...]:
        names = list(self._feature_set.feature_names)
        x = train[names]
        y = train["target"].to_numpy(dtype=int)
        splitter = RepeatedStratifiedKFold(
            n_splits=self._plan.cv_splits,
            n_repeats=self._plan.cv_repeats,
            random_state=self._plan.random_seed,
        )
        metric_names = ("precision", "recall", "f1", "roc_auc", "pr_auc")
        collected: dict[str, list[float]] = {name: [] for name in metric_names}
        for fit_indices, score_indices in splitter.split(x, y):
            pipeline = self._pipeline(profile)
            pipeline.fit(x.iloc[fit_indices], y[fit_indices])
            probabilities = pipeline.predict_proba(x.iloc[score_indices])[:, 1]
            metrics = binary_metrics(y[score_indices], probabilities, profile.threshold)
            for name in collected:
                collected[name].append(float(getattr(metrics, name)))
        return tuple(
            (
                name,
                MetricDistribution(
                    mean=float(np.mean(values)),
                    standard_deviation=float(np.std(values, ddof=1)),
                ),
            )
            for name, values in collected.items()
        )

    def _pipeline(self, profile: ModelProfile) -> Pipeline:
        categorical = [
            feature.name
            for feature in self._feature_set.features
            if feature.dtype is FeatureType.CATEGORY
        ]
        numeric = [
            feature.name
            for feature in self._feature_set.features
            if feature.dtype is not FeatureType.CATEGORY
        ]
        preprocessor = ColumnTransformer(
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
                    numeric,
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
                    categorical,
                ),
            ]
        )
        params: dict[str, Any] = profile.parameter_dict()
        if profile.kind is ModelKind.LOGISTIC_REGRESSION:
            estimator = LogisticRegression(random_state=self._random_seed, **params)
        elif profile.kind is ModelKind.RANDOM_FOREST:
            estimator = RandomForestClassifier(random_state=self._random_seed, **params)
        else:
            raise ValueError(f"unsupported model kind: {profile.kind}")
        return Pipeline([("preprocessor", preprocessor), ("model", estimator)])


def binary_metrics(
    target: np.ndarray[Any, Any],
    probabilities: np.ndarray[Any, Any],
    threshold: float,
) -> BinaryMetrics:
    """Calculate thresholded classification and ranking metrics."""
    predictions = (probabilities >= threshold).astype(int)
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        target, predictions, labels=[0, 1]
    ).ravel()
    return BinaryMetrics(
        precision=float(precision_score(target, predictions, zero_division=0)),
        recall=float(recall_score(target, predictions, zero_division=0)),
        f1=float(f1_score(target, predictions, zero_division=0)),
        roc_auc=float(roc_auc_score(target, probabilities)),
        pr_auc=float(average_precision_score(target, probabilities)),
        true_negative=int(true_negative),
        false_positive=int(false_positive),
        false_negative=int(false_negative),
        true_positive=int(true_positive),
    )


def bootstrap_recall_lower(
    target: np.ndarray[Any, Any],
    probabilities: np.ndarray[Any, Any],
    threshold: float,
    *,
    iterations: int,
    confidence_level: float,
    random_seed: int,
) -> float:
    """Estimate the lower recall confidence bound with deterministic resampling."""
    rng = np.random.default_rng(random_seed)
    indices = np.arange(len(target))
    recalls: list[float] = []
    while len(recalls) < iterations:
        sample = rng.choice(indices, size=len(indices), replace=True)
        if len(np.unique(target[sample])) < 2:
            continue
        predictions = (probabilities[sample] >= threshold).astype(int)
        recalls.append(float(recall_score(target[sample], predictions)))
    alpha = 1 - confidence_level
    return float(np.quantile(recalls, alpha / 2))
