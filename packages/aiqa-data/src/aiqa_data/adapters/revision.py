"""Strict benchmark split revision configuration adapter."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aiqa_data.domain import BenchmarkSplitRevision


class BenchmarkSplitRevisionDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    revision: str = Field(min_length=1)
    parent_revision: str = Field(min_length=1)
    random_seed: int
    parent_test_train_count: int = Field(gt=0)
    rationale: str = Field(min_length=1)

    def to_domain(self) -> BenchmarkSplitRevision:
        return BenchmarkSplitRevision(
            revision=self.revision,
            parent_revision=self.parent_revision,
            random_seed=self.random_seed,
            parent_test_train_count=self.parent_test_train_count,
        )


def load_split_revision(path: Path) -> BenchmarkSplitRevision:
    with path.open(encoding="utf-8") as file:
        payload: Any = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("split revision root must be a mapping")
    return BenchmarkSplitRevisionDocument.model_validate(payload).to_domain()
