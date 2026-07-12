"""Conversion between model evaluation values and QA release evidence."""

from aiqa_model.domain import ProfileEvaluation
from aiqa_qa.domain import ModelEvidence


def model_evidence_from_profile(evaluation: ProfileEvaluation) -> ModelEvidence:
    """Extract the QA guardrail values from one immutable model profile evaluation."""
    metrics = evaluation.metrics
    return ModelEvidence(
        profile=evaluation.profile,
        precision=metrics.precision,
        recall=metrics.recall,
        pr_auc=metrics.pr_auc,
        false_negative=metrics.false_negative,
        bootstrap_recall_lower=evaluation.bootstrap_recall_lower,
    )
