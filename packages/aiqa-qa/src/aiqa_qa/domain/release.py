"""Release decision domain values and guardrail evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class Decision(StrEnum):
    """Allowed outcomes for a candidate release evaluation."""

    APPROVE = "APPROVE"
    HOLD = "HOLD"


class ReleaseCheck(StrEnum):
    """Stable guardrail names emitted in release decision evidence."""

    RECALL_GUARDRAIL = "recall_guardrail"
    PRECISION_FLOOR = "precision_floor"
    RECALL_UNCERTAINTY = "recall_uncertainty"
    PR_AUC_VS_BASELINE = "pr_auc_vs_baseline"
    FALSE_NEGATIVE_REDUCTION = "false_negative_reduction"


@dataclass(frozen=True)
class ModelEvidence:
    """Validated quality evidence for one model profile at one lifecycle stage."""

    profile: str
    precision: float
    recall: float
    pr_auc: float
    false_negative: int
    bootstrap_recall_lower: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.profile, str)
            or not self.profile
            or self.profile != self.profile.strip()
        ):
            raise ValueError(
                "model evidence profile must be a non-empty trimmed string"
            )
        metric_values = (
            self.precision,
            self.recall,
            self.pr_auc,
            self.bootstrap_recall_lower,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or not 0 <= value <= 1
            for value in metric_values
        ):
            raise ValueError(
                "model evidence metrics must be finite values from zero to one"
            )
        if (
            not isinstance(self.false_negative, int)
            or isinstance(self.false_negative, bool)
            or self.false_negative < 0
        ):
            raise ValueError("false-negative count must be a non-negative integer")
        if self.bootstrap_recall_lower > self.recall:
            raise ValueError("bootstrap recall lower bound cannot exceed recall")


@dataclass(frozen=True)
class ReleasePolicy:
    """Configured candidate identities and quality guardrails for one release."""

    name: str
    disclaimer: str
    baseline_profile: str
    candidate_a_profile: str
    candidate_b_profile: str
    minimum_recall: float
    recall_safety_margin: float
    minimum_recall_bootstrap_lower: float
    minimum_precision: float
    minimum_pr_auc_delta_vs_baseline: float
    minimum_false_negative_reduction: int

    def __post_init__(self) -> None:
        profile_names = (
            self.baseline_profile,
            self.candidate_a_profile,
            self.candidate_b_profile,
        )
        if (
            not isinstance(self.name, str)
            or not self.name
            or self.name != self.name.strip()
        ):
            raise ValueError("release policy name must be a non-empty trimmed string")
        if (
            not isinstance(self.disclaimer, str)
            or not self.disclaimer
            or self.disclaimer != self.disclaimer.strip()
        ):
            raise ValueError(
                "release policy disclaimer must be a non-empty trimmed string"
            )
        if any(
            not isinstance(name, str) or not name or name != name.strip()
            for name in profile_names
        ):
            raise ValueError(
                "release policy profile names must be non-empty trimmed strings"
            )
        if len(profile_names) != len(set(profile_names)):
            raise ValueError("release policy profile names must be unique")
        bounded_metrics = (
            self.minimum_recall,
            self.recall_safety_margin,
            self.minimum_recall_bootstrap_lower,
            self.minimum_precision,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or not 0 <= value <= 1
            for value in bounded_metrics
        ):
            raise ValueError(
                "release policy bounded metrics must be finite values from zero to one"
            )
        if self.minimum_recall + self.recall_safety_margin > 1:
            raise ValueError("release policy recall guardrail cannot exceed one")
        if (
            isinstance(self.minimum_pr_auc_delta_vs_baseline, bool)
            or not isinstance(self.minimum_pr_auc_delta_vs_baseline, (int, float))
            or not isfinite(self.minimum_pr_auc_delta_vs_baseline)
            or not -1 <= self.minimum_pr_auc_delta_vs_baseline <= 1
        ):
            raise ValueError(
                "release policy PR-AUC delta must be finite from minus one to one"
            )
        if (
            not isinstance(self.minimum_false_negative_reduction, int)
            or isinstance(self.minimum_false_negative_reduction, bool)
            or self.minimum_false_negative_reduction < 0
        ):
            raise ValueError(
                "release policy false-negative reduction must be a non-negative integer"
            )

    @property
    def candidate_profiles(self) -> tuple[str, str]:
        """Return the deterministic candidate profile order owned by this policy."""
        return (self.candidate_a_profile, self.candidate_b_profile)

    @property
    def profile_names(self) -> tuple[str, str, str]:
        """Return baseline and candidates in the exact configured policy order."""
        return (self.baseline_profile, *self.candidate_profiles)


@dataclass(frozen=True)
class ReleaseDecision:
    """Decision and all guardrail outcomes for one candidate profile."""

    profile: str
    decision: Decision
    checks: tuple[tuple[ReleaseCheck, bool], ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.profile, str)
            or not self.profile
            or self.profile != self.profile.strip()
        ):
            raise ValueError(
                "release decision profile must be a non-empty trimmed string"
            )
        if not isinstance(self.decision, Decision):
            raise ValueError("release decision must be a Decision")
        if tuple(check for check, _ in self.checks) != tuple(ReleaseCheck):
            raise ValueError("release decision must contain every guardrail in order")
        if any(not isinstance(passed, bool) for _, passed in self.checks):
            raise ValueError("release decision checks must contain boolean outcomes")
        expected = (
            Decision.APPROVE
            if all(passed for _, passed in self.checks)
            else Decision.HOLD
        )
        if self.decision is not expected:
            raise ValueError("release decision does not match its guardrail outcomes")


def decide_release(
    policy: ReleasePolicy,
    baseline: ModelEvidence,
    candidate: ModelEvidence,
) -> ReleaseDecision:
    """Evaluate one candidate against the policy and one baseline evidence value."""
    checks = (
        (
            ReleaseCheck.RECALL_GUARDRAIL,
            candidate.recall >= policy.minimum_recall + policy.recall_safety_margin,
        ),
        (
            ReleaseCheck.PRECISION_FLOOR,
            candidate.precision >= policy.minimum_precision,
        ),
        (
            ReleaseCheck.RECALL_UNCERTAINTY,
            candidate.bootstrap_recall_lower >= policy.minimum_recall_bootstrap_lower,
        ),
        (
            ReleaseCheck.PR_AUC_VS_BASELINE,
            candidate.pr_auc - baseline.pr_auc
            >= policy.minimum_pr_auc_delta_vs_baseline,
        ),
        (
            ReleaseCheck.FALSE_NEGATIVE_REDUCTION,
            baseline.false_negative - candidate.false_negative
            >= policy.minimum_false_negative_reduction,
        ),
    )
    return ReleaseDecision(
        profile=candidate.profile,
        decision=(
            Decision.APPROVE if all(passed for _, passed in checks) else Decision.HOLD
        ),
        checks=checks,
    )
