"""Strict quality rule configuration adapter."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RawQualityRules(BaseModel):
    """Validated raw-record quality limits from versioned YAML."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_record_count: int = Field(gt=0)
    minimum_observation_count: int = Field(gt=0)
    maximum_minute: int = Field(gt=0)


class ProcessedQualityRules(BaseModel):
    """Validated processed-feature quality limits from versioned YAML."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_row_count: int = Field(gt=0)
    expected_positive_count: int = Field(gt=0)
    target_values: tuple[int, ...]
    missing_indicator_values: tuple[float, ...]


class QualityRules(BaseModel):
    """Complete validated quality policy for raw and processed evidence."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    raw: RawQualityRules
    processed: ProcessedQualityRules


def load_quality_rules(path: Path) -> QualityRules:
    """Load one versioned quality-policy YAML document."""
    with path.open(encoding="utf-8") as file:
        payload: Any = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("quality rule root must be a mapping")
    return QualityRules.model_validate(payload)
