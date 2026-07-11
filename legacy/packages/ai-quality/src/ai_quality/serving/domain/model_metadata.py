"""Model metadata domain object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata that connects training and serving."""

    model_name: str
    model_version: str
    dataset_version: str
    feature_columns: tuple[str, ...]
    target_column: str
    positive_label: str
    negative_label: str
    label_mapping: dict[str, str]

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ModelMetadata:
        """Build metadata from configs/validation/model_metadata.yaml."""
        return cls(
            model_name=str(config["model_name"]),
            model_version=str(config["model_version"]),
            dataset_version=str(config["dataset_version"]),
            feature_columns=tuple(config["feature_columns"]),
            target_column=str(config["target_column"]),
            positive_label=str(config["positive_label"]),
            negative_label=str(config["negative_label"]),
            label_mapping=dict(config["label_mapping"]),
        )
