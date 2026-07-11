"""Education-only release assurance policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Decision(StrEnum):
    APPROVE = "APPROVE"
    HOLD = "HOLD"


@dataclass(frozen=True)
class ModelEvidence:
    profile: str
    precision: float
    recall: float
    pr_auc: float
    false_negative: int
    bootstrap_recall_lower: float


@dataclass(frozen=True)
class ReleasePolicy:
    name: str
    minimum_recall: float
    recall_safety_margin: float
    minimum_recall_bootstrap_lower: float
    minimum_precision: float
    minimum_pr_auc_delta_vs_baseline: float
    minimum_false_negative_reduction: int


@dataclass(frozen=True)
class ReleaseDecision:
    profile: str
    decision: Decision
    checks: tuple[tuple[str, bool], ...]


def decide_release(
    policy: ReleasePolicy,
    baseline: ModelEvidence,
    candidate: ModelEvidence,
) -> ReleaseDecision:
    checks = (
        (
            "recall_guardrail",
            candidate.recall >= policy.minimum_recall + policy.recall_safety_margin,
        ),
        ("precision_floor", candidate.precision >= policy.minimum_precision),
        (
            "recall_uncertainty",
            candidate.bootstrap_recall_lower >= policy.minimum_recall_bootstrap_lower,
        ),
        (
            "pr_auc_vs_baseline",
            candidate.pr_auc - baseline.pr_auc
            >= policy.minimum_pr_auc_delta_vs_baseline,
        ),
        (
            "false_negative_reduction",
            baseline.false_negative - candidate.false_negative
            >= policy.minimum_false_negative_reduction,
        ),
    )
    decision = (
        Decision.APPROVE if all(passed for _, passed in checks) else Decision.HOLD
    )
    return ReleaseDecision(
        profile=candidate.profile,
        decision=decision,
        checks=checks,
    )
