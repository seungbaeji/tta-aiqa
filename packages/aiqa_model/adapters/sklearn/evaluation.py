"""Sklearn profile scoring, cross-validation, and metric calculations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import pandas as pd
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

from aiqa_model.domain import (
    BinaryMetrics,
    EvaluationPlan,
    MetricDistribution,
    ModelProfile,
    ProfileEvaluation,
)


class ProbabilityPipeline(Protocol):
    """Sklearn-compatible fitted pipeline that exposes positive-class probabilities."""

    def predict_proba(self, values: pd.DataFrame) -> np.ndarray[Any, Any]:
        """Return class probability columns for the supplied feature frame."""


@dataclass(frozen=True)
class SklearnProfileEvaluator:
    """Evaluate profile pipelines against pandas model datasets."""

    feature_names: tuple[str, ...]
    evaluation_plan: EvaluationPlan
    random_seed: int
    pipeline_builder: Callable[[ModelProfile], Pipeline]

    def evaluate(
        self,
        profile: ModelProfile,
        fit: pd.DataFrame,
        score: pd.DataFrame,
        *,
        include_cross_validation: bool,
    ) -> ProfileEvaluation:
        """Fit one profile, score it, and optionally summarize repeated CV metrics."""
        pipeline = self.pipeline_builder(profile)
        pipeline.fit(
            fit[list(self.feature_names)], fit["target"].to_numpy(dtype=int)
        )
        probabilities = pipeline.predict_proba(score[list(self.feature_names)])[:, 1]
        target = score["target"].to_numpy(dtype=int)
        return ProfileEvaluation(
            profile=profile.name,
            threshold=profile.threshold,
            metrics=binary_metrics(target, probabilities, profile.threshold),
            bootstrap_recall_lower=bootstrap_recall_lower(
                target,
                probabilities,
                profile.threshold,
                iterations=self.evaluation_plan.bootstrap_iterations,
                confidence_level=self.evaluation_plan.confidence_level,
                random_seed=self.random_seed,
            ),
            cross_validation=(
                self.cross_validate(profile, fit) if include_cross_validation else ()
            ),
        )

    def evaluate_fitted(
        self,
        profile: ModelProfile,
        pipeline: ProbabilityPipeline,
        score: pd.DataFrame,
    ) -> ProfileEvaluation:
        """Score a supplied frozen pipeline without fitting or tuning it again."""
        probabilities = pipeline.predict_proba(score[list(self.feature_names)])[:, 1]
        target = score["target"].to_numpy(dtype=int)
        return ProfileEvaluation(
            profile=profile.name,
            threshold=profile.threshold,
            metrics=binary_metrics(target, probabilities, profile.threshold),
            bootstrap_recall_lower=bootstrap_recall_lower(
                target,
                probabilities,
                profile.threshold,
                iterations=self.evaluation_plan.bootstrap_iterations,
                confidence_level=self.evaluation_plan.confidence_level,
                random_seed=self.random_seed,
            ),
            cross_validation=(),
        )

    def cross_validate(
        self, profile: ModelProfile, train: pd.DataFrame
    ) -> tuple[tuple[str, MetricDistribution], ...]:
        """Return repeated stratified-CV metric distributions for one profile."""
        features = train[list(self.feature_names)]
        target = train["target"].to_numpy(dtype=int)
        splitter = RepeatedStratifiedKFold(
            n_splits=self.evaluation_plan.cv_splits,
            n_repeats=self.evaluation_plan.cv_repeats,
            random_state=self.evaluation_plan.random_seed,
        )
        metric_names = self.evaluation_plan.cross_validation_metric_names
        collected: dict[str, list[float]] = {name: [] for name in metric_names}
        for fit_indices, score_indices in splitter.split(features, target):
            pipeline = self.pipeline_builder(profile)
            pipeline.fit(features.iloc[fit_indices], target[fit_indices])
            probabilities = pipeline.predict_proba(features.iloc[score_indices])[:, 1]
            metrics = binary_metrics(
                target[score_indices], probabilities, profile.threshold
            )
            for name in metric_names:
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


def binary_metrics(
    target: np.ndarray[Any, Any],
    probabilities: np.ndarray[Any, Any],
    threshold: float,
) -> BinaryMetrics:
    """Calculate thresholded classification and probability-ranking metrics."""
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
    if len(target) == 0 or len(np.unique(target)) < 2:
        raise ValueError("bootstrap recall requires both binary target classes")
    random = np.random.default_rng(random_seed)
    indices = np.arange(len(target))
    recalls: list[float] = []
    while len(recalls) < iterations:
        sample = random.choice(indices, size=len(indices), replace=True)
        if len(np.unique(target[sample])) < 2:
            continue
        predictions = (probabilities[sample] >= threshold).astype(int)
        recalls.append(float(recall_score(target[sample], predictions)))
    alpha = 1 - confidence_level
    return float(np.quantile(recalls, alpha / 2))
