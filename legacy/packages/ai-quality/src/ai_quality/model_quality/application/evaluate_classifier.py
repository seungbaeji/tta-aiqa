"""Evaluate binary classifier scores."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ai_quality.common.labels import NEGATIVE_LABEL, POSITIVE_LABEL, normalize_label
from ai_quality.model_quality.domain.confusion_matrix import (
    build_confusion_matrix,
)
from ai_quality.model_quality.domain.evaluation_report import EvaluationReport
from ai_quality.model_quality.domain.metric_result import BinaryMetricResult
from ai_quality.model_quality.domain.threshold_policy import (
    ThresholdComparison,
    ThresholdPolicy,
)


@dataclass(frozen=True)
class EvaluateClassifier:
    """Build evaluation reports from labels and positive-class scores."""

    dataset_name: str
    threshold: float

    def run(
        self,
        labels: Sequence[object],
        scores: Sequence[float],
    ) -> EvaluationReport:
        """Return an evaluation report for one threshold."""
        return calculate_binary_metrics(
            labels=labels,
            scores=scores,
            threshold=self.threshold,
            dataset_name=self.dataset_name,
        )


# docs:start calculate_binary_metrics
def calculate_binary_metrics(
    labels: Sequence[object],
    scores: Sequence[float],
    threshold: float,
    dataset_name: str = "dataset",
) -> EvaluationReport:
    """Calculate binary metrics from labels, scores, and threshold."""
    if len(labels) != len(scores):
        msg = "labels and scores must have the same length"
        raise ValueError(msg)

    valid_labels, valid_scores = collect_valid_binary_pairs(labels, scores)
    predictions = ThresholdPolicy(threshold=threshold).predict_many(valid_scores)
    confusion_matrix = build_confusion_matrix(valid_labels, predictions)
    binary_labels = [
        1 if normalize_label(label) == POSITIVE_LABEL else 0
        for label in valid_labels
    ]

    metrics = BinaryMetricResult(
        accuracy=confusion_matrix.accuracy,
        precision=confusion_matrix.precision,
        recall=confusion_matrix.recall,
        f1_score=confusion_matrix.f1_score,
        auroc=calculate_auroc(binary_labels, valid_scores),
        pr_auc=calculate_average_precision(binary_labels, valid_scores),
    )

    return EvaluationReport(
        dataset_name=dataset_name,
        threshold=threshold,
        row_count=len(valid_labels),
        confusion_matrix=confusion_matrix,
        metrics=metrics,
    )
# docs:end calculate_binary_metrics


def collect_valid_binary_pairs(
    labels: Sequence[object],
    scores: Sequence[float],
) -> tuple[list[str], list[float]]:
    """Return labels and scores that can be used for binary metrics."""
    valid_labels: list[str] = []
    valid_scores: list[float] = []

    for label, score in zip(labels, scores, strict=True):
        normalized_label = normalize_label(label)
        numeric_score = float(score)

        if normalized_label not in {POSITIVE_LABEL, NEGATIVE_LABEL}:
            continue
        if numeric_score != numeric_score:
            continue

        valid_labels.append(normalized_label)
        valid_scores.append(numeric_score)

    return valid_labels, valid_scores


def evaluate_thresholds(
    labels: Sequence[object],
    scores: Sequence[float],
    thresholds: Sequence[float],
) -> list[ThresholdComparison]:
    """Return Precision/Recall trade-off rows for threshold candidates."""
    comparisons: list[ThresholdComparison] = []
    for threshold in thresholds:
        report = calculate_binary_metrics(labels, scores, float(threshold))
        comparisons.append(
            ThresholdComparison(
                threshold=float(threshold),
                precision=report.metrics.precision,
                recall=report.metrics.recall,
                false_positive=report.confusion_matrix.false_positive,
                false_negative=report.confusion_matrix.false_negative,
            )
        )
    return comparisons


def calculate_auroc(labels: Sequence[int], scores: Sequence[float]) -> float | None:
    """Calculate AUROC with average ranks for tied scores."""
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    if positive_count == 0 or negative_count == 0:
        return None

    ranks = average_ranks(scores)
    positive_rank_sum = sum(
        rank for rank, label in zip(ranks, labels, strict=True) if label == 1
    )
    return (
        positive_rank_sum - positive_count * (positive_count + 1) / 2
    ) / (positive_count * negative_count)


def average_ranks(scores: Sequence[float]) -> list[float]:
    """Return 1-based average ranks in ascending score order."""
    indexed_scores = sorted((float(score), index) for index, score in enumerate(scores))
    ranks = [0.0] * len(indexed_scores)
    position = 0

    while position < len(indexed_scores):
        next_position = position + 1
        while (
            next_position < len(indexed_scores)
            and indexed_scores[next_position][0] == indexed_scores[position][0]
        ):
            next_position += 1

        average_rank = (position + 1 + next_position) / 2
        for rank_position in range(position, next_position):
            original_index = indexed_scores[rank_position][1]
            ranks[original_index] = average_rank
        position = next_position

    return ranks


def calculate_average_precision(
    labels: Sequence[int],
    scores: Sequence[float],
) -> float | None:
    """Calculate average precision as a PR-AUC style summary."""
    positive_count = sum(labels)
    if positive_count == 0:
        return None

    sorted_pairs = sorted(
        zip(scores, labels, strict=True),
        key=lambda pair: float(pair[0]),
        reverse=True,
    )
    true_positive = 0
    precision_sum = 0.0

    for rank, (_, label) in enumerate(sorted_pairs, start=1):
        if label == 1:
            true_positive += 1
            precision_sum += true_positive / rank

    return precision_sum / positive_count
