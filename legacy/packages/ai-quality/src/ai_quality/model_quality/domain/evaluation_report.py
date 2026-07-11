"""Evaluation report domain objects."""

from __future__ import annotations

from dataclasses import dataclass

from ai_quality.model_quality.domain.confusion_matrix import ConfusionMatrixCounts
from ai_quality.model_quality.domain.metric_result import BinaryMetricResult


@dataclass(frozen=True)
class EvaluationReport:
    """Model evaluation report for one dataset and threshold."""

    dataset_name: str
    threshold: float
    row_count: int
    confusion_matrix: ConfusionMatrixCounts
    metrics: BinaryMetricResult


@dataclass(frozen=True)
class DatasetComparison:
    """Comparison between baseline and current dataset evaluation."""

    baseline: EvaluationReport
    candidate: EvaluationReport
    accuracy_delta: float
    precision_delta: float
    recall_delta: float
    f1_delta: float
    qa_notes: tuple[str, ...]
