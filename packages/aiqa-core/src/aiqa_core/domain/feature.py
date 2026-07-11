"""Feature contract domain values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeatureType(StrEnum):
    FLOAT = "float"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CATEGORY = "category"


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    dtype: FeatureType
    nullable: bool

    def __post_init__(self) -> None:
        if not self.name or self.name.strip() != self.name:
            raise ValueError("feature name must be non-empty and trimmed")


@dataclass(frozen=True)
class FeatureSet:
    schema_version: int
    name: str
    target: str
    features: tuple[FeatureDefinition, ...]

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("schema version must be positive")
        if not self.name:
            raise ValueError("feature set name must not be empty")
        if not self.features:
            raise ValueError("feature set must contain at least one feature")
        names = self.feature_names
        if len(names) != len(set(names)):
            raise ValueError("feature names must be unique")
        if self.target in names:
            raise ValueError("target must not be included in model features")

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(feature.name for feature in self.features)
