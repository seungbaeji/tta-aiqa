"""Threshold policy helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ai_quality.common.labels import NEGATIVE_LABEL, POSITIVE_LABEL


@dataclass(frozen=True)
class ThresholdPolicy:
    """Decision rule that converts score into prediction."""

    threshold: float
    positive_label: str = POSITIVE_LABEL
    negative_label: str = NEGATIVE_LABEL

    def predict_one(self, score: float) -> str:
        """Convert one score into a class label."""
        if score >= self.threshold:
            return self.positive_label
        return self.negative_label

    def predict_many(self, scores: Sequence[float]) -> list[str]:
        """Convert scores into class labels."""
        return [self.predict_one(float(score)) for score in scores]


@dataclass(frozen=True)
class ThresholdComparison:
    """Metric result for one threshold candidate."""

    threshold: float
    precision: float
    recall: float
    false_positive: int
    false_negative: int
