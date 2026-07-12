"""Evaluate all configured candidate profiles against one baseline."""

from __future__ import annotations

from dataclasses import dataclass

from aiqa_qa.domain import ModelEvidence, ReleaseDecision, ReleasePolicy, decide_release


@dataclass(frozen=True)
class ReleaseEvaluation:
    """One policy evaluation containing a baseline and ordered candidate decisions."""

    baseline: ModelEvidence
    decisions: tuple[ReleaseDecision, ...]

    def __post_init__(self) -> None:
        if not self.decisions:
            raise ValueError("release evaluation requires candidate decisions")


def evaluate_candidate_releases(
    *,
    policy: ReleasePolicy,
    baseline: ModelEvidence,
    candidates: tuple[ModelEvidence, ...],
) -> ReleaseEvaluation:
    """Evaluate the exact candidate profiles configured by one release policy."""
    if baseline.profile != policy.baseline_profile:
        raise ValueError("baseline profile does not match the release policy")
    candidate_profiles = tuple(candidate.profile for candidate in candidates)
    if candidate_profiles != policy.candidate_profiles:
        raise ValueError("candidate profiles do not match the release policy")
    return ReleaseEvaluation(
        baseline=baseline,
        decisions=tuple(
            decide_release(policy, baseline, candidate) for candidate in candidates
        ),
    )
