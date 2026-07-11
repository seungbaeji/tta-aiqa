"""Metric result domain objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BinaryMetricResult:
    """Binary classification metrics used in the course."""

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auroc: float | None
    pr_auc: float | None

    def as_percentages(self) -> dict[str, float | None]:
        """Return metrics scaled to percentages for reports."""
        return {
            "accuracy": self.accuracy * 100,
            "precision": self.precision * 100,
            "recall": self.recall * 100,
            "f1_score": self.f1_score * 100,
            "auroc": None if self.auroc is None else self.auroc * 100,
            "pr_auc": None if self.pr_auc is None else self.pr_auc * 100,
        }
