"""Runtime settings for the Model Trainer process."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelTrainerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIQA_MODEL_",
        env_file=".env.model-trainer",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    environment: str = "local"
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
