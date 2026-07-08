"""Inspect dataset quality before model evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ai_quality.data_quality.domain.dataset_schema import DatasetSchema
from ai_quality.data_quality.domain.quality_report import (
    ColumnQuality,
    QualityReport,
    RangeCheckResult,
    calculate_label_support,
)
from ai_quality.data_quality.domain.quality_rule import DataQualityRules
from ai_quality.data_quality.ports.dataset_reader import DatasetReader


@dataclass(frozen=True)
class InspectDatasetQuality:
    """Run the data quality checks needed before model evaluation."""

    dataset_reader: DatasetReader
    schema: DatasetSchema
    rules: DataQualityRules

    def run(self, dataset_path: Path) -> QualityReport:
        """Read a dataset and return a quality report."""
        dataframe = self.dataset_reader.read(dataset_path)
        numeric_dataframe = coerce_numeric_columns(
            dataframe=dataframe,
            columns=[rule.column for rule in self.rules.valid_ranges],
        )

        return QualityReport(
            row_count=len(dataframe),
            column_count=len(dataframe.columns),
            missing_columns=tuple(
                self.schema.find_missing_columns(set(dataframe.columns))
            ),
            column_quality=tuple(build_column_quality(dataframe)),
            range_results=tuple(
                build_range_results(numeric_dataframe, self.rules)
            ),
            label_support=calculate_label_support(
                list(dataframe.get(self.schema.target_column, []))
            ),
        )


def coerce_numeric_columns(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Return a copy with selected columns coerced to numeric values."""
    numeric_dataframe = dataframe.copy()
    for column in columns:
        if column in numeric_dataframe.columns:
            numeric_dataframe[column] = pd.to_numeric(
                numeric_dataframe[column],
                errors="coerce",
            )
    return numeric_dataframe


def build_column_quality(dataframe: pd.DataFrame) -> list[ColumnQuality]:
    """Build column-level missing and uniqueness summaries."""
    row_count = len(dataframe)
    summaries: list[ColumnQuality] = []

    for column in dataframe.columns:
        missing_count = int(dataframe[column].isnull().sum())
        missing_ratio = missing_count / row_count * 100.0 if row_count > 0 else 0.0
        summaries.append(
            ColumnQuality(
                column=str(column),
                dtype=str(dataframe[column].dtype),
                missing_count=missing_count,
                missing_ratio=missing_ratio,
                unique_count=int(dataframe[column].nunique(dropna=True)),
            )
        )

    return summaries


def build_range_results(
    dataframe: pd.DataFrame,
    rules: DataQualityRules,
) -> list[RangeCheckResult]:
    """Build range validation results for numeric columns."""
    results: list[RangeCheckResult] = []
    row_count = len(dataframe)

    for valid_range in rules.valid_ranges:
        if valid_range.column not in dataframe.columns:
            continue

        invalid_mask = dataframe[valid_range.column].notna() & (
            (dataframe[valid_range.column] < valid_range.min_value)
            | (dataframe[valid_range.column] > valid_range.max_value)
        )
        invalid_count = int(invalid_mask.sum())
        invalid_ratio = invalid_count / row_count * 100.0 if row_count > 0 else 0.0
        results.append(
            RangeCheckResult(
                column=valid_range.column,
                min_value=valid_range.min_value,
                max_value=valid_range.max_value,
                invalid_count=invalid_count,
                invalid_ratio=invalid_ratio,
            )
        )

    return results

