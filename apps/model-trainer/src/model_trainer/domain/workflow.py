"""Framework-independent values for one Model Trainer lifecycle request."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class TrainerStage(StrEnum):
    """Named lifecycle stages available to the Model Trainer process."""

    DEVELOPMENT = "development"
    DIAGNOSTICS = "diagnostics"
    BOOTSTRAP = "bootstrap"
    RECONCILE_BOOTSTRAP = "reconcile-bootstrap"
    FINAL = "final"
    RECONCILE_FINAL = "reconcile-final"


@dataclass(frozen=True)
class TrainerCommand:
    """Internal request for exactly one model lifecycle stage."""

    stage: TrainerStage
    sealed_test_token: str | None = None

    def __post_init__(self) -> None:
        if self.stage is TrainerStage.FINAL and not self.sealed_test_token:
            raise ValueError("final evaluation requires a sealed test token")
        if self.stage is not TrainerStage.FINAL and self.sealed_test_token is not None:
            raise ValueError("sealed test token is only valid for final evaluation")


@dataclass(frozen=True)
class ModelTrainerConfiguration:
    """Resolved filesystem and tracking inputs for one trainer process invocation."""

    repository_root: Path
    feature_contract_path: Path
    feature_sets_path: Path
    profiles_path: Path
    evaluation_path: Path
    release_policy_path: Path
    split_dataset_dir: Path
    split_config_path: Path
    data_manifest_path: Path
    mlflow_tracking_uri: str
    mlflow_experiment_name: str
    dvc_lock_path: Path
    artifact_dir: Path
    development_evidence_path: Path
    feature_diagnostics_path: Path
    model_bundle_dir: Path
    deployed_model_dir: Path
    bootstrap_manifest_path: Path
    bootstrap_evidence_path: Path
    freeze_manifest_path: Path
    release_manifest_path: Path
    canonical_evidence_path: Path
