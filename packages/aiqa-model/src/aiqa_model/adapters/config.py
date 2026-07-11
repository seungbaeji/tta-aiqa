"""Strict model profile and evaluation configuration adapters."""

from pathlib import Path
from typing import Any

import yaml
from aiqa_core.domain import ModelRole
from pydantic import BaseModel, ConfigDict, Field

from aiqa_model.domain import EvaluationPlan, ModelKind, ModelProfile


class ProfileDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    model_role: ModelRole
    candidate_id: str | None = None
    kind: ModelKind
    threshold: float = Field(gt=0, lt=1)
    params: dict[str, Any]

    def to_domain(self) -> ModelProfile:
        return ModelProfile(
            name=self.name,
            model_role=self.model_role,
            candidate_id=self.candidate_id,
            kind=self.kind,
            threshold=self.threshold,
            params=tuple(sorted(self.params.items())),
        )


class ProfilesDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    random_seed: int
    profiles: tuple[ProfileDocument, ...] = Field(min_length=1)


class CrossValidationDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    splits: int = Field(ge=2)
    repeats: int = Field(ge=1)
    random_seed: int


class BootstrapDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    iterations: int = Field(ge=1)
    confidence_level: float = Field(gt=0, lt=1)


class EvaluationDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    cross_validation: CrossValidationDocument
    bootstrap: BootstrapDocument
    ranking_metrics: tuple[str, ...]
    operating_metrics: tuple[str, ...]

    def to_domain(self) -> EvaluationPlan:
        return EvaluationPlan(
            cv_splits=self.cross_validation.splits,
            cv_repeats=self.cross_validation.repeats,
            random_seed=self.cross_validation.random_seed,
            bootstrap_iterations=self.bootstrap.iterations,
            confidence_level=self.bootstrap.confidence_level,
        )


def load_profiles(path: Path) -> tuple[int, tuple[ModelProfile, ...]]:
    document = ProfilesDocument.model_validate(_mapping(path))
    profiles = tuple(item.to_domain() for item in document.profiles)
    names = [profile.name for profile in profiles]
    if len(names) != len(set(names)):
        raise ValueError("model profile names must be unique")
    return document.random_seed, profiles


def load_evaluation_plan(path: Path) -> EvaluationPlan:
    return EvaluationDocument.model_validate(_mapping(path)).to_domain()


def _mapping(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        payload: Any = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("model configuration root must be a mapping")
    return payload
