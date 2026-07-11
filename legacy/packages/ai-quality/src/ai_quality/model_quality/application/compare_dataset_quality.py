"""Compare model quality across datasets."""

from __future__ import annotations

from ai_quality.model_quality.domain.evaluation_report import (
    DatasetComparison,
    EvaluationReport,
)


# docs:start compare_baseline_current_results
def compare_baseline_current_results(
    baseline: EvaluationReport,
    current: EvaluationReport,
) -> DatasetComparison:
    """Compare baseline and current evaluation reports for QA interpretation."""
    accuracy_delta = current.metrics.accuracy - baseline.metrics.accuracy
    precision_delta = current.metrics.precision - baseline.metrics.precision
    recall_delta = current.metrics.recall - baseline.metrics.recall
    f1_delta = current.metrics.f1_score - baseline.metrics.f1_score

    notes: list[str] = []
    if recall_delta < -0.05:
        notes.append("Recall dropped. Check label quality and missing features.")
    if precision_delta < -0.05:
        notes.append("Precision dropped. Check outliers and false positive growth.")
    if (
        current.confusion_matrix.false_negative
        > baseline.confusion_matrix.false_negative
    ):
        notes.append("False negatives increased. Review threshold and support.")
    if (
        current.confusion_matrix.false_positive
        > baseline.confusion_matrix.false_positive
    ):
        notes.append("False positives increased. Review score distribution.")

    return DatasetComparison(
        baseline=baseline,
        candidate=current,
        accuracy_delta=accuracy_delta,
        precision_delta=precision_delta,
        recall_delta=recall_delta,
        f1_delta=f1_delta,
        qa_notes=tuple(notes),
    )
# docs:end compare_baseline_current_results
