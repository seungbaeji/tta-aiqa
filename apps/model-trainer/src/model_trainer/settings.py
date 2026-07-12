"""Runtime settings for the Model Trainer process."""

from pathlib import Path

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from model_trainer.workflow import ModelTrainerConfiguration


class ModelTrainerSettings(BaseSettings):
    """Validate environment and Secret-backed inputs for model training."""

    model_config = SettingsConfigDict(
        env_prefix="AIQA_MODEL_",
        env_file=".env.model-trainer",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    environment: str = "local"
    telemetry_config_path: Path = Path("configs/observability/telemetry.yaml")
    otlp_endpoint: AnyHttpUrl | None = None
    feature_contract_path: Path
    feature_sets_path: Path
    profiles_path: Path
    evaluation_path: Path
    release_policy_path: Path
    split_dataset_dir: Path
    split_config_path: Path = Path("params.yaml")
    data_manifest_path: Path = Path(
        "reference/evidence/data-lineage/data-manifest.json"
    )
    mlflow_tracking_uri: str
    mlflow_experiment_name: str = "tta-aiqa-physionet-2012"
    dvc_lock_path: Path = Path("dvc.lock")
    model_implementation_path: Path = Path(
        "packages/aiqa-model/src/aiqa_model/adapters/sklearn_benchmark.py"
    )
    release_implementation_path: Path = Path(
        "packages/aiqa-qa/src/aiqa_qa/domain/release.py"
    )
    trainer_implementation_path: Path = Path(
        "apps/model-trainer/src/model_trainer/bootstrap.py"
    )
    tracking_implementation_path: Path = Path(
        "packages/aiqa-model/src/aiqa_model/adapters/mlflow_tracker.py"
    )
    artifact_dir: Path
    development_evidence_path: Path = Path(
        "reference/evidence/model/development-benchmark.json"
    )
    feature_diagnostics_path: Path = Path(
        "reference/evidence/model/feature-diagnostics.json"
    )
    model_bundle_dir: Path
    deployed_model_dir: Path = Path("artifacts/models/deployed")
    bootstrap_manifest_path: Path = Path("artifacts/model/model-bootstrap.json")
    bootstrap_evidence_path: Path = Path(
        "reference/evidence/model/model-bootstrap.json"
    )
    freeze_manifest_path: Path
    canonical_evidence_path: Path = Path(
        "reference/evidence/model/canonical-benchmark.json"
    )

    def to_configuration(self) -> ModelTrainerConfiguration:
        """Convert external runtime settings into internal workflow configuration."""
        return ModelTrainerConfiguration(
            feature_contract_path=self.feature_contract_path,
            feature_sets_path=self.feature_sets_path,
            profiles_path=self.profiles_path,
            evaluation_path=self.evaluation_path,
            release_policy_path=self.release_policy_path,
            split_dataset_dir=self.split_dataset_dir,
            split_config_path=self.split_config_path,
            data_manifest_path=self.data_manifest_path,
            mlflow_tracking_uri=self.mlflow_tracking_uri,
            mlflow_experiment_name=self.mlflow_experiment_name,
            dvc_lock_path=self.dvc_lock_path,
            model_implementation_path=self.model_implementation_path,
            release_implementation_path=self.release_implementation_path,
            trainer_implementation_path=self.trainer_implementation_path,
            tracking_implementation_path=self.tracking_implementation_path,
            artifact_dir=self.artifact_dir,
            development_evidence_path=self.development_evidence_path,
            feature_diagnostics_path=self.feature_diagnostics_path,
            model_bundle_dir=self.model_bundle_dir,
            deployed_model_dir=self.deployed_model_dir,
            bootstrap_manifest_path=self.bootstrap_manifest_path,
            bootstrap_evidence_path=self.bootstrap_evidence_path,
            freeze_manifest_path=self.freeze_manifest_path,
            canonical_evidence_path=self.canonical_evidence_path,
        )
