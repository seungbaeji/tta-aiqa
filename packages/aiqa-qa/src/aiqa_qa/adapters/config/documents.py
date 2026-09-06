"""Validated external DTOs for release policy YAML documents."""

from pydantic import BaseModel, ConfigDict, Field

from aiqa_qa.domain import ReleasePolicy


class ReleaseRulesDocument(BaseModel):
    """External guardrail thresholds for one release policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_recall: float = Field(ge=0, le=1)
    recall_safety_margin: float = Field(ge=0, le=1)
    minimum_recall_bootstrap_lower: float = Field(ge=0, le=1)
    minimum_precision: float = Field(ge=0, le=1)
    minimum_pr_auc_delta_vs_baseline: float = Field(ge=-1, le=1)
    minimum_false_negative_reduction: int = Field(ge=0)


class ReleasePolicyDocument(BaseModel):
    """Root DTO for one versioned education release policy document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    name: str
    baseline_profile: str
    candidate_a_profile: str
    candidate_b_profile: str
    rules: ReleaseRulesDocument
    disclaimer: str

    def to_domain(self) -> ReleasePolicy:
        """Convert validated YAML values into the immutable release policy."""
        return ReleasePolicy(
            name=self.name,
            disclaimer=self.disclaimer,
            baseline_profile=self.baseline_profile,
            candidate_a_profile=self.candidate_a_profile,
            candidate_b_profile=self.candidate_b_profile,
            **self.rules.model_dump(),
        )
