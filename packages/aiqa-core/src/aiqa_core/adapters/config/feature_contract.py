"""Strict YAML adapter for the canonical model input contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aiqa_core.domain.feature import FeatureDefinition, FeatureSet, FeatureType


class FeatureDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    dtype: FeatureType
    nullable: bool


class FeatureContractDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    name: str = Field(min_length=1)
    target: str = Field(min_length=1)
    features: tuple[FeatureDocument, ...] = Field(min_length=1)

    def to_domain(self) -> FeatureSet:
        return FeatureSet(
            schema_version=self.schema_version,
            name=self.name,
            target=self.target,
            features=tuple(
                FeatureDefinition(
                    name=feature.name,
                    dtype=feature.dtype,
                    nullable=feature.nullable,
                )
                for feature in self.features
            ),
        )


def load_feature_contract(path: Path) -> FeatureSet:
    payload: Any
    with path.open(encoding="utf-8") as file:
        payload = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("feature contract root must be a mapping")
    return FeatureContractDocument.model_validate(payload).to_domain()
