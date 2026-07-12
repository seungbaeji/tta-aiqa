"""Runtime settings for the Data Quality Pipeline process."""

from pathlib import Path

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from data_quality_pipeline.workflow import DataQualityPaths


class DataQualitySettings(BaseSettings):
    """Validate environment-backed inputs for a data-quality process run."""

    model_config = SettingsConfigDict(
        env_prefix="AIQA_DATA_",
        env_file=".env.data-quality",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    environment: str = "local"
    telemetry_config_path: Path = Path("configs/observability/telemetry.yaml")
    otlp_endpoint: AnyHttpUrl | None = None
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

    def to_paths(self) -> DataQualityPaths:
        """Convert external settings into framework-neutral workflow values."""
        return DataQualityPaths(
            source_contract_path=self.source_contract_path,
            aggregation_config_path=self.aggregation_config_path,
            split_config_path=self.split_config_path,
            patient_features_path=self.patient_features_path,
            split_manifest_path=self.split_manifest_path,
            split_dataset_dir=self.split_dataset_dir,
            source_evidence_path=self.source_evidence_path,
            split_revision_config_path=self.split_revision_config_path,
            revision_split_manifest_path=self.revision_split_manifest_path,
            revision_split_dataset_dir=self.revision_split_dataset_dir,
            quality_rules_path=self.quality_rules_path,
            validation_artifact_dir=self.validation_artifact_dir,
        )
