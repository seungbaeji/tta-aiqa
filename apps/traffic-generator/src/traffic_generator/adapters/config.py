"""Strict traffic scenario configuration adapter."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from traffic_generator.domain import (
    FeatureTransform,
    InvalidTrafficCase,
    ScenarioMode,
    TrafficPlan,
)


class DefaultsDocument(BaseModel):
    """Default request count, interval, and timeout for all scenarios."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_count: int = Field(gt=0)
    interval_seconds: float = Field(ge=0)
    timeout_seconds: float = Field(gt=0)


class TransformDocument(BaseModel):
    """External numeric transform configuration for one feature."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    add: float = 0.0
    multiply: float = 1.0
    minimum: float | None = None
    maximum: float | None = None


class ScenarioDocument(BaseModel):
    """External overrides and behavior configuration for one named scenario."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: ScenarioMode
    request_count: int | None = Field(default=None, gt=0)
    interval_seconds: float | None = Field(default=None, ge=0)
    timeout_seconds: float | None = Field(default=None, gt=0)
    transforms: dict[str, TransformDocument] = Field(default_factory=dict)
    invalid_cases: tuple[InvalidTrafficCase, ...] = ()


class TrafficConfig(BaseModel):
    """Validated external traffic configuration converted into immutable plans."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    random_seed: int
    defaults: DefaultsDocument
    scenarios: dict[str, ScenarioDocument] = Field(min_length=1)

    def plans(self) -> dict[str, TrafficPlan]:
        """Build one immutable domain plan for every configured scenario name."""
        return {
            name: TrafficPlan(
                name=name,
                mode=document.mode,
                request_count=(
                    self.defaults.request_count
                    if document.request_count is None
                    else document.request_count
                ),
                interval_seconds=(
                    self.defaults.interval_seconds
                    if document.interval_seconds is None
                    else document.interval_seconds
                ),
                timeout_seconds=(
                    self.defaults.timeout_seconds
                    if document.timeout_seconds is None
                    else document.timeout_seconds
                ),
                transforms=tuple(
                    FeatureTransform(feature=feature, **transform.model_dump())
                    for feature, transform in document.transforms.items()
                ),
                invalid_cases=document.invalid_cases,
            )
            for name, document in self.scenarios.items()
        }


def load_traffic_config(path: Path) -> TrafficConfig:
    """Load and validate one versioned YAML traffic scenario configuration."""
    with path.open(encoding="utf-8") as file:
        payload: Any = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("traffic config root must be a mapping")
    return TrafficConfig.model_validate(payload)
