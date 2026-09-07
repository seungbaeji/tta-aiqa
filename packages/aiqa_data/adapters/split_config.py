"""Pydantic adapter for deterministic dataset split configuration."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aiqa_data.adapters.source.yaml import load_yaml_mapping
from aiqa_data.adapters.split import StratifiedSplitConfig


class SplitParametersDocument(BaseModel):
    """Validate ratio and seed values nested under the data configuration key."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    random_seed: int
    train_ratio: float = Field(gt=0, lt=1)
    valid_ratio: float = Field(gt=0, lt=1)
    test_ratio: float = Field(gt=0, lt=1)
    operational_ratio: float = Field(gt=0, lt=1)


class DataParametersDocument(BaseModel):
    """Validate the external parameter document consumed by the split adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    data: SplitParametersDocument


def load_split_config(path: Path) -> StratifiedSplitConfig:
    """Load one versioned split configuration as an immutable adapter value."""
    document = DataParametersDocument.model_validate(load_yaml_mapping(path))
    return StratifiedSplitConfig(**document.data.model_dump())
