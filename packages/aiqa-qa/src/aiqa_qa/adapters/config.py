"""Strict release policy configuration adapter."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aiqa_qa.domain import ReleasePolicy


class ReleaseRulesDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_recall: float = Field(ge=0, le=1)
    recall_safety_margin: float = Field(ge=0, le=1)
    minimum_recall_bootstrap_lower: float = Field(ge=0, le=1)
    minimum_precision: float = Field(ge=0, le=1)
    minimum_pr_auc_delta_vs_baseline: float
    minimum_false_negative_reduction: int = Field(ge=0)


class ReleasePolicyDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    name: str
    baseline_profile: str
    candidate_a_profile: str
    candidate_b_profile: str
    rules: ReleaseRulesDocument
    disclaimer: str

    def to_domain(self) -> ReleasePolicy:
        return ReleasePolicy(name=self.name, **self.rules.model_dump())


def load_release_policy(path: Path) -> tuple[ReleasePolicyDocument, ReleasePolicy]:
    with path.open(encoding="utf-8") as file:
        payload: Any = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("release policy root must be a mapping")
    document = ReleasePolicyDocument.model_validate(payload)
    return document, document.to_domain()
