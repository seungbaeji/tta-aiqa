"""Pandas dataset reader and standardization adapter."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_quality.common.labels import LABEL_MAP
from ai_quality.data_quality.domain.dataset_schema import DatasetSchema


class PandasDatasetReader:
    """Read and standardize CSV datasets for the course."""

    def __init__(self, schema: DatasetSchema) -> None:
        self._schema = schema

    def read(self, dataset_path: Path) -> pd.DataFrame:
        """Read a CSV dataset and apply the course schema."""
        return load_and_standardize_dataset(dataset_path, self._schema)


# docs:start load_and_standardize_dataset
def load_and_standardize_dataset(
    dataset_path: Path,
    schema: DatasetSchema,
) -> pd.DataFrame:
    """Load a CSV file and normalize column names and labels."""
    dataframe = pd.read_csv(dataset_path)
    dataframe = dataframe.rename(columns=schema.column_rename_map)

    if schema.target_column in dataframe.columns:
        dataframe[schema.target_column] = dataframe[schema.target_column].replace(
            LABEL_MAP
        )

    if "timestamp" in dataframe.columns:
        dataframe["timestamp"] = pd.to_datetime(
            dataframe["timestamp"],
            errors="coerce",
        )

    return dataframe
# docs:end load_and_standardize_dataset

