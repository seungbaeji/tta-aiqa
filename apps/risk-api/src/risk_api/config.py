"""Strict Risk API configuration adapter."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskMetricNames(BaseModel):
    """Names for the bounded metrics owned by the Risk API."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_count: str = Field(min_length=1)
    request_latency: str = Field(min_length=1)
    prediction_count: str = Field(min_length=1)
    score: str = Field(min_length=1)
    missing_features: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_names(self) -> "RiskMetricNames":
        values = tuple(self.model_dump().values())
        if len(values) != len(set(values)):
            raise ValueError("Risk API metric names must be unique")
        return self


class RiskMetricBuckets(BaseModel):
    """Histogram buckets tuned for the Risk API's fixed metric meanings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_latency: tuple[float, ...]
    score: tuple[float, ...]
    missing_features: tuple[float, ...]

    @model_validator(mode="after")
    def validate_sorted_buckets(self) -> "RiskMetricBuckets":
        for name, values in self.model_dump().items():
            invalid = (
                not values
                or tuple(sorted(values)) != values
                or len(values) != len(set(values))
            )
            if invalid:
                raise ValueError(f"Risk API {name} buckets must be unique and sorted")
        return self


class RiskApiObservabilityConfig(BaseModel):
    """Application-owned metric and cardinality policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed_scenarios: tuple[str, ...]
    fallback_scenario: str = Field(min_length=1)
    unmatched_route: str = Field(min_length=1)
    allowed_methods: tuple[str, ...]
    fallback_method: str = Field(min_length=1)
    request_metric_labels: tuple[str, ...]
    prediction_metric_labels: tuple[str, ...]
    metrics: RiskMetricNames
    buckets: RiskMetricBuckets

    @model_validator(mode="after")
    def validate_cardinality_policy(self) -> "RiskApiObservabilityConfig":
        if not self.allowed_scenarios:
            raise ValueError("Risk API allowed scenarios are required")
        if len(self.allowed_scenarios) != len(set(self.allowed_scenarios)):
            raise ValueError("Risk API allowed scenarios must be unique")
        if self.fallback_scenario not in self.allowed_scenarios:
            raise ValueError("Risk API fallback scenario must be allowed")
        if not self.allowed_methods:
            raise ValueError("Risk API allowed methods are required")
        if len(self.allowed_methods) != len(set(self.allowed_methods)):
            raise ValueError("Risk API allowed methods must be unique")
        if self.fallback_method not in self.allowed_methods:
            raise ValueError("Risk API fallback method must be allowed")
        forbidden = {"request_id", "run_id", "span_id", "trace_id"}
        for labels in (self.request_metric_labels, self.prediction_metric_labels):
            if not labels or len(labels) != len(set(labels)):
                raise ValueError("Risk API metric labels must be non-empty and unique")
            if forbidden & set(labels):
                raise ValueError(
                    "Risk API metric labels contain an unbounded identifier"
                )
        if set(self.request_metric_labels) != {
            "service_name",
            "environment",
            "route",
            "method",
            "status_code",
        }:
            raise ValueError("Risk API request metric labels are invalid")
        if set(self.prediction_metric_labels) != {
            "service_name",
            "environment",
            "model_profile",
            "model_version",
            "scenario",
            "prediction",
        }:
            raise ValueError("Risk API prediction metric labels are invalid")
        return self


class ApiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    title: str = Field(min_length=1)
    api_version: str = Field(pattern=r"^v[1-9][0-9]*$")
    request_id_header: str = Field(min_length=1)
    scenario_header: str = Field(min_length=1)
    positive_label: str = Field(min_length=1)
    negative_label: str = Field(min_length=1)
    score_decimal_places: int = Field(ge=0, le=12)
    education_only: bool
    observability: RiskApiObservabilityConfig


def load_api_config(path: Path) -> ApiConfig:
    with path.open(encoding="utf-8") as file:
        payload: Any = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("Risk API config root must be a mapping")
    return ApiConfig.model_validate(payload)
