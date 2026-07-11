"""Dataset schema definitions for the course data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DatasetSchema:
    """Column groups used by data quality checks."""

    required_columns: tuple[str, ...]
    model_feature_columns: tuple[str, ...]
    derived_feature_columns: tuple[str, ...]
    metadata_columns: tuple[str, ...]
    target_column: str
    column_rename_map: dict[str, str]

    @property
    def all_feature_columns(self) -> tuple[str, ...]:
        """Return original model features plus optional derived features."""
        return self.model_feature_columns + self.derived_feature_columns

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> DatasetSchema:
        """Build a schema from configs/validation/dataset_schema.yaml."""
        return cls(
            required_columns=tuple(config["required_columns"]),
            model_feature_columns=tuple(config["model_feature_columns"]),
            derived_feature_columns=tuple(config.get("derived_feature_columns", [])),
            metadata_columns=tuple(config.get("metadata_columns", [])),
            target_column=str(config["target_column"]),
            column_rename_map=dict(config.get("column_rename_map", {})),
        )

    def find_missing_columns(self, columns: set[str]) -> list[str]:
        """Return required columns that are absent from a dataset."""
        return [column for column in self.required_columns if column not in columns]

