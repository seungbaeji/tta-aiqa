"""Strict data aggregation configuration adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aiqa_data.domain import (
    AggregationPlan,
    SeriesFeatureRule,
    StaticFeatureRule,
    Statistic,
)


class StaticRuleDocument(BaseModel):
    """Validate one external static-feature aggregation rule."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    parameter: str = Field(min_length=1)
    output_name: str = Field(min_length=1)


class SeriesRuleDocument(StaticRuleDocument):
    """Validate one external time-series aggregation rule."""

    statistics: tuple[Statistic, ...] = Field(min_length=1)


class AggregationDocument(BaseModel):
    """Validate the external YAML aggregation document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    missing_sentinel: float
    static_features: tuple[StaticRuleDocument, ...]
    series_features: tuple[SeriesRuleDocument, ...]

    def to_domain(self) -> AggregationPlan:
        """Convert validated YAML values to an immutable aggregation plan."""
        return AggregationPlan(
            missing_sentinel=self.missing_sentinel,
            static_features=tuple(
                StaticFeatureRule(item.parameter, item.output_name)
                for item in self.static_features
            ),
            series_features=tuple(
                SeriesFeatureRule(item.parameter, item.output_name, item.statistics)
                for item in self.series_features
            ),
        )


def load_aggregation_plan(path: Path) -> AggregationPlan:
    """Load one versioned aggregation plan from YAML."""
    payload: Any
    with path.open(encoding="utf-8") as file:
        payload = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("aggregation config root must be a mapping")
    return AggregationDocument.model_validate(payload).to_domain()
