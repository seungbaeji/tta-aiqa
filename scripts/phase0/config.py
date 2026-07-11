"""Typed configuration for the Phase 0 feasibility experiment."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Reject unknown configuration keys."""

    model_config = ConfigDict(extra="forbid")


class SourceConfig(StrictModel):
    records_dir: Path
    archive_path: Path
    outcomes_path: Path
    expected_record_count: int = Field(gt=0)
    expected_death_count: int = Field(gt=0)
    archive_sha256: str = Field(min_length=64, max_length=64)
    outcomes_sha256: str = Field(min_length=64, max_length=64)
    target_column: str
    blocked_outcome_columns: tuple[str, ...]


class SeriesAggregation(StrictModel):
    output_name: str
    statistics: tuple[Literal["min", "max", "mean", "last", "count", "sum"], ...]


class AggregationConfig(StrictModel):
    missing_sentinel: float
    static_parameters: dict[str, str]
    series_parameters: dict[str, SeriesAggregation]


class SplitConfig(StrictModel):
    random_seed: int
    train_ratio: float = Field(gt=0, lt=1)
    valid_ratio: float = Field(gt=0, lt=1)
    test_ratio: float = Field(gt=0, lt=1)
    release_holdout_ratio: float = Field(gt=0, lt=1)

    @model_validator(mode="after")
    def ratios_total_one(self) -> SplitConfig:
        total = (
            self.train_ratio
            + self.valid_ratio
            + self.test_ratio
            + self.release_holdout_ratio
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"split ratios must total 1.0, got {total}")
        return self


class ModelSpec(StrictModel):
    name: str
    kind: Literal["dummy", "logistic_regression", "random_forest"]
    params: dict[str, Any]


class EvaluationConfig(StrictModel):
    cv_splits: int = Field(ge=2)
    cv_repeats: int = Field(ge=1)
    bootstrap_iterations: int = Field(ge=100)
    threshold_min: float = Field(gt=0, lt=1)
    threshold_max: float = Field(gt=0, lt=1)
    threshold_step: float = Field(gt=0, lt=1)
    baseline_profile: str
    minimum_pr_auc_lift_over_dummy: float = Field(ge=0)
    recall_guardrail: float = Field(gt=0, lt=1)
    recall_safety_margin: float = Field(ge=0, lt=1)
    minimum_recall_bootstrap_lower: float = Field(ge=0, lt=1)
    minimum_precision: float = Field(gt=0, lt=1)
    minimum_pr_auc_delta_vs_baseline: float
    minimum_fn_reduction_vs_baseline: int = Field(ge=0)
    candidate_a_minimum_recall: float = Field(ge=0, lt=1)
    candidate_a_profiles: tuple[str, ...]
    candidate_b_profiles: tuple[str, ...]
    models: tuple[ModelSpec, ...]

    @model_validator(mode="after")
    def references_exist(self) -> EvaluationConfig:
        names = [model.name for model in self.models]
        if len(names) != len(set(names)):
            raise ValueError("model names must be unique")
        referenced = {
            self.baseline_profile,
            *self.candidate_a_profiles,
            *self.candidate_b_profiles,
        }
        missing = referenced - set(names)
        if missing:
            raise ValueError(f"unknown model profiles: {sorted(missing)}")
        if "dummy_prior" not in names:
            raise ValueError("dummy_prior model is required")
        if self.threshold_min >= self.threshold_max:
            raise ValueError("threshold_min must be less than threshold_max")
        return self


class OutputConfig(StrictModel):
    artifact_dir: Path
    evidence_dir: Path


class Phase0Config(StrictModel):
    schema_version: Literal[1]
    source: SourceConfig
    aggregation: AggregationConfig
    split: SplitConfig
    evaluation: EvaluationConfig
    outputs: OutputConfig


def load_config(path: Path) -> Phase0Config:
    """Load and validate a Phase 0 YAML configuration."""
    with path.open(encoding="utf-8") as file:
        raw = yaml.safe_load(file)
    return Phase0Config.model_validate(raw)
