"""Runtime settings for the Data Quality Pipeline process."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class DataQualitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIQA_DATA_",
        env_file=".env.data-quality",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    environment: str = "local"
    source_contract_path: Path
    aggregation_config_path: Path
    split_config_path: Path
    patient_features_path: Path
    split_manifest_path: Path
    split_dataset_dir: Path
    split_revision_config_path: Path | None = None
    revision_split_manifest_path: Path | None = None
    revision_split_dataset_dir: Path | None = None
    source_evidence_path: Path
    quality_rules_path: Path | None = None
    validation_artifact_dir: Path | None = None
