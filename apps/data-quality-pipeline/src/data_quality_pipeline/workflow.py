"""Internal data-quality workflow values shared by CLI and DVC adapters."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DataQualityStage(StrEnum):
    """Named workflow stages supported by the data-quality process."""

    VERIFY_SOURCE = "verify-source"
    EXTRACT = "extract"
    AGGREGATE = "aggregate"
    SPLIT = "split"
    REVISE_SPLIT = "revise-split"
    VALIDATE = "validate"


@dataclass(frozen=True)
class DataQualityPaths:
    """Resolved filesystem locations used by one data-quality workflow run."""

    source_contract_path: Path
    aggregation_config_path: Path
    split_config_path: Path
    patient_features_path: Path
    split_manifest_path: Path
    split_dataset_dir: Path
    source_evidence_path: Path
    split_revision_config_path: Path | None = None
    revision_split_manifest_path: Path | None = None
    revision_split_dataset_dir: Path | None = None
    quality_rules_path: Path | None = None
    validation_artifact_dir: Path | None = None


@dataclass(frozen=True)
class DataPreparationResult:
    """Outcome emitted by one data-quality stage."""

    command: str
    rows: int | None = None
    features: int | None = None
    success: bool | None = None
