"""Confusion matrix domain object."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ai_quality.common.labels import NEGATIVE_LABEL, POSITIVE_LABEL, normalize_label


@dataclass(frozen=True)
class ConfusionMatrixCounts:
    """Binary confusion matrix counts for QA interpretation."""

    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int

    @property
    def total(self) -> int:
        """Return total evaluated samples."""
        return (
            self.true_positive
            + self.false_positive
            + self.false_negative
            + self.true_negative
        )

    @property
    def accuracy(self) -> float:
        """Return accuracy."""
        if self.total == 0:
            return 0.0
        return (self.true_positive + self.true_negative) / self.total

    @property
    def precision(self) -> float:
        """Return precision for the positive class."""
        denominator = self.true_positive + self.false_positive
        if denominator == 0:
            return 0.0
        return self.true_positive / denominator

    @property
    def recall(self) -> float:
        """Return recall for the positive class."""
        denominator = self.true_positive + self.false_negative
        if denominator == 0:
            return 0.0
        return self.true_positive / denominator

    @property
    def f1_score(self) -> float:
        """Return F1-score for the positive class."""
        denominator = self.precision + self.recall
        if denominator == 0:
            return 0.0
        return 2 * self.precision * self.recall / denominator


# docs:start build_confusion_matrix
def build_confusion_matrix(
    labels: Sequence[object],
    predictions: Sequence[object],
    positive_label: str = POSITIVE_LABEL,
    negative_label: str = NEGATIVE_LABEL,
) -> ConfusionMatrixCounts:
    """Build binary confusion matrix counts from labels and predictions."""
    if len(labels) != len(predictions):
        msg = "labels and predictions must have the same length"
        raise ValueError(msg)

    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0

    for label, prediction in zip(labels, predictions, strict=True):
        normalized_label = normalize_label(label)
        normalized_prediction = normalize_label(prediction)

        if (
            normalized_label == positive_label
            and normalized_prediction == positive_label
        ):
            true_positive += 1
        elif (
            normalized_label == negative_label
            and normalized_prediction == positive_label
        ):
            false_positive += 1
        elif (
            normalized_label == positive_label
            and normalized_prediction == negative_label
        ):
            false_negative += 1
        elif (
            normalized_label == negative_label
            and normalized_prediction == negative_label
        ):
            true_negative += 1

    return ConfusionMatrixCounts(
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        true_negative=true_negative,
    )
# docs:end build_confusion_matrix
