"""Feature contract domain values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeatureType(StrEnum):
    """Primitive types allowed by the canonical model-input contract."""

    FLOAT = "float"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CATEGORY = "category"


@dataclass(frozen=True)
class FeatureDefinition:
    """One immutable feature declaration in the canonical input contract."""

    name: str
    dtype: FeatureType
    nullable: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name
            or self.name.strip() != self.name
        ):
            raise ValueError("feature name must be non-empty and trimmed")
        if not isinstance(self.dtype, FeatureType):
            raise ValueError("feature dtype must be a FeatureType")
        if not isinstance(self.nullable, bool):
            raise ValueError("feature nullable must be a bool")


@dataclass(frozen=True)
class FeatureSet:
    """Versioned canonical model-input contract shared across contexts."""

    schema_version: int
    name: str
    target: str
    features: tuple[FeatureDefinition, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version < 1
        ):
            raise ValueError("schema version must be positive")
        if (
            not isinstance(self.name, str)
            or not self.name
            or self.name.strip() != self.name
        ):
            raise ValueError("feature set name must be non-empty and trimmed")
        if (
            not isinstance(self.target, str)
            or not self.target
            or self.target.strip() != self.target
        ):
            raise ValueError("feature set target must be non-empty and trimmed")
        if not isinstance(self.features, tuple) or not self.features:
            raise ValueError("feature set must contain at least one feature")
        if not all(isinstance(feature, FeatureDefinition) for feature in self.features):
            raise ValueError("feature set must contain FeatureDefinition values")
        names = self.feature_names
        if len(names) != len(set(names)):
            raise ValueError("feature names must be unique")
        if self.target in names:
            raise ValueError("target must not be included in model features")

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Return feature names in canonical model-input order."""
        return tuple(feature.name for feature in self.features)
