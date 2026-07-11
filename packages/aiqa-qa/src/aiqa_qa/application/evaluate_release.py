"""Evaluate all configured candidate profiles against one baseline."""

from __future__ import annotations

from dataclasses import dataclass

from aiqa_qa.domain import ModelEvidence, ReleaseDecision, ReleasePolicy, decide_release


@dataclass(frozen=True)
class ReleaseEvaluation:
    baseline: ModelEvidence
    decisions: tuple[ReleaseDecision, ...]


class EvaluateCandidateReleases:
    def __init__(self, policy: ReleasePolicy) -> None:
        self._policy = policy

    def execute(
        self,
        *,
        baseline: ModelEvidence,
        candidates: tuple[ModelEvidence, ...],
    ) -> ReleaseEvaluation:
        if any(candidate.profile == baseline.profile for candidate in candidates):
            raise ValueError("baseline cannot be evaluated as a candidate")
        if len({candidate.profile for candidate in candidates}) != len(candidates):
            raise ValueError("candidate profiles must be unique")
        return ReleaseEvaluation(
            baseline=baseline,
            decisions=tuple(
                decide_release(self._policy, baseline, candidate)
                for candidate in candidates
            ),
        )
