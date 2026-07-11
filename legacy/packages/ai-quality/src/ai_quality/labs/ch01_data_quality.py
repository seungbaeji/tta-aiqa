"""Shared helpers for chapter 1 labs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_quality.common.config import load_yaml
from ai_quality.common.paths import config_path, data_path
from ai_quality.data_quality.domain.dataset_schema import DatasetSchema
from ai_quality.data_quality.domain.quality_rule import DataQualityRules
from ai_quality.data_quality.infrastructure.pandas_dataset_reader import (
    load_and_standardize_dataset,
)


def load_schema() -> DatasetSchema:
    """Load chapter 1 dataset schema."""
    return DatasetSchema.from_config(
        load_yaml(config_path("validation", "dataset_schema.yaml"))
    )


def load_rules() -> DataQualityRules:
    """Load chapter 1 quality rules."""
    return DataQualityRules.from_config(
        load_yaml(config_path("validation", "data_quality_rules.yaml"))
    )


def chapter_dataset_path() -> Path:
    """Return the chapter 1 dataset path."""
    return data_path("vital_signs_evaluation_baseline.csv")


def load_chapter_dataframe() -> pd.DataFrame:
    """Load the chapter 1 dataframe with a helpful error message."""
    dataset_path = chapter_dataset_path()
    if not dataset_path.exists():
        msg = (
            f"Dataset not found: {dataset_path}\n"
            "Run: uv run python labs/prepare_data.py"
        )
        raise FileNotFoundError(msg)

    return load_and_standardize_dataset(dataset_path, load_schema())


def print_section(title: str) -> None:
    """Print a compact section heading for command-line labs."""
    print(f"\n[{title}]")
