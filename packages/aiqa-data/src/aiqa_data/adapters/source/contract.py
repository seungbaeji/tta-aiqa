"""Pydantic adapters for the versioned PhysioNet source contract."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aiqa_data.adapters.source.yaml import load_yaml_mapping


@dataclass(frozen=True)
class PhysioNetSourceConfig:
    """Resolved source locations and structural constraints for PhysioNet 2012."""

    source_manifest_path: Path
    records_dir: Path
    outcomes_path: Path
    expected_record_count: int
    expected_death_count: int
    target_column: str
    blocked_outcome_columns: tuple[str, ...]
    observation_window_hours: int


class PhysioNetSourceDocument(BaseModel):
    """Validate the external YAML contract for one PhysioNet source revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    dataset: str = Field(min_length=1)
    source_manifest_path: Path
    records_dir: Path
    outcomes_path: Path
    expected_record_count: int = Field(gt=0)
    expected_death_count: int = Field(gt=0)
    record_columns: tuple[str, str, str]
    record_id_parameter: str
    target_column: str
    blocked_outcome_columns: tuple[str, ...]
    observation_window_hours: int = Field(gt=0)

    def to_config(self) -> PhysioNetSourceConfig:
        """Convert validated external values to a framework-neutral source config."""
        if self.record_columns != ("Time", "Parameter", "Value"):
            raise ValueError("unsupported PhysioNet record columns")
        if self.record_id_parameter != "RecordID":
            raise ValueError("unsupported PhysioNet record identifier")
        return PhysioNetSourceConfig(
            source_manifest_path=self.source_manifest_path,
            records_dir=self.records_dir,
            outcomes_path=self.outcomes_path,
            expected_record_count=self.expected_record_count,
            expected_death_count=self.expected_death_count,
            target_column=self.target_column,
            blocked_outcome_columns=self.blocked_outcome_columns,
            observation_window_hours=self.observation_window_hours,
        )


def load_source_contract(path: Path) -> PhysioNetSourceConfig:
    """Load and validate one versioned PhysioNet source contract."""
    return PhysioNetSourceDocument.model_validate(load_yaml_mapping(path)).to_config()
