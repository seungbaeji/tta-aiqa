"""Pydantic DTOs for release evaluation JSON evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aiqa_qa.application import ReleaseEvaluation
from aiqa_qa.domain import Decision, ReleaseCheck, ReleaseDecision


class ReleaseDecisionDocument(BaseModel):
    """Serialized decision and guardrail outcomes for one candidate profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str
    decision: Decision
    checks: dict[ReleaseCheck, bool]

    @classmethod
    def from_domain(cls, decision: ReleaseDecision) -> ReleaseDecisionDocument:
        """Convert one immutable domain decision into its evidence DTO."""
        return cls(
            profile=decision.profile,
            decision=decision.decision,
            checks=dict(decision.checks),
        )


class ReleaseEvaluationEvidenceDocument(BaseModel):
    """Root DTO for one versioned release evaluation evidence document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    evaluation_role: Literal["valid", "test"]
    baseline_profile: str
    decisions: tuple[ReleaseDecisionDocument, ...] = Field(min_length=1)
    provenance: dict[str, str]

    @classmethod
    def from_application(
        cls,
        result: ReleaseEvaluation,
        *,
        evaluation_role: Literal["valid", "test"],
        provenance: dict[str, str],
    ) -> ReleaseEvaluationEvidenceDocument:
        """Convert a release evaluation into its canonical JSON evidence DTO."""
        return cls(
            schema_version=1,
            evaluation_role=evaluation_role,
            baseline_profile=result.baseline.profile,
            decisions=tuple(
                ReleaseDecisionDocument.from_domain(decision)
                for decision in result.decisions
            ),
            provenance=provenance,
        )
