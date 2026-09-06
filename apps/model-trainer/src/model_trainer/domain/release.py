"""Immutable app-domain values for a frozen model release."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FrozenModelBundle:
    """One serialized model and metadata pair selected for release evaluation."""

    profile: str
    model_path: Path
    metadata_path: Path
    mlflow_run_id: str

    def __post_init__(self) -> None:
        if not self.profile or self.profile != self.profile.strip():
            raise ValueError("frozen model profile must be a non-empty trimmed string")
        if not self.mlflow_run_id or self.mlflow_run_id != self.mlflow_run_id.strip():
            raise ValueError("frozen model requires an MLflow run ID")


@dataclass(frozen=True)
class FrozenRelease:
    """Verified pre-test source identity and model artifacts for final evaluation."""

    source_commit: str
    bundles: tuple[FrozenModelBundle, ...]

    def __post_init__(self) -> None:
        if not self.source_commit or self.source_commit != self.source_commit.strip():
            raise ValueError("frozen release requires a source commit")
        if not self.bundles:
            raise ValueError("frozen release requires at least one model bundle")
