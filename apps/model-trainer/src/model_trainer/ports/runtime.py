"""Focused external capabilities for the Model Trainer process."""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from aiqa_core.domain import FeatureSet
from aiqa_model.domain import (
    BenchmarkResult,
    FeatureDiagnostics,
    ModelProfile,
    ProfileEvaluation,
)
from aiqa_qa.domain import ReleaseDecision

from model_trainer.domain import (
    FrozenModelBundle,
    FrozenRelease,
    ModelTrainerConfiguration,
)


class JsonDocumentStore(Protocol):
    """Persist and retrieve reviewable JSON object documents."""

    def read(self, path: Path) -> dict[str, object]:
        """Load one JSON object from the configured artifact location."""

    def write(self, document: Mapping[str, object], path: Path) -> Path:
        """Persist one JSON object using deterministic formatting."""


class BootstrapEvidenceStore(Protocol):
    """Render bootstrap results as local artifacts and portable review evidence."""

    def candidate_deployment_reason(
        self, configuration: ModelTrainerConfiguration
    ) -> str:
        """Explain why a bootstrap operation cannot deploy a candidate model."""

    def persist(
        self,
        document: Mapping[str, object],
        configuration: ModelTrainerConfiguration,
    ) -> Path:
        """Validate and write local bootstrap output plus portable evidence."""

    def reconcile(self, configuration: ModelTrainerConfiguration) -> Path:
        """Regenerate portable evidence from the immutable local bootstrap artifact."""


class BaselineModelPublisher(Protocol):
    """Publish only the initialized baseline bundle to a deployment location."""

    def publish(self, configuration: ModelTrainerConfiguration) -> None:
        """Copy baseline files and write their local deployment identity document."""


class ModelEvidenceCodec(Protocol):
    """Translate model domain results to and from versioned evidence documents."""

    def benchmark_document(self, result: BenchmarkResult) -> dict[str, object]:
        """Serialize one benchmark result into a validated JSON-safe object."""

    def benchmark_result(self, document: Mapping[str, object]) -> BenchmarkResult:
        """Parse a validated benchmark result from one JSON object."""

    def diagnostics_document(self, result: FeatureDiagnostics) -> dict[str, object]:
        """Serialize development-only feature diagnostics into an evidence object."""


class BenchmarkRunTracker(Protocol):
    """Record one benchmark result with its evidence and provenance in MLflow."""

    def record(
        self,
        result: BenchmarkResult,
        evidence_path: Path,
        provenance: dict[str, str],
    ) -> tuple[str, ...]:
        """Return MLflow run IDs in the benchmark profile order."""


class ModelRunTracker(Protocol):
    """Record one serialized fitted model and its development lineage in MLflow."""

    def record(
        self,
        *,
        profile: ModelProfile,
        evaluation: ProfileEvaluation,
        pipeline: object,
        bundle_dir: Path,
        train_path: Path,
        valid_path: Path,
        provenance: dict[str, str],
    ) -> str:
        """Return the MLflow run ID for one fitted model artifact."""


class ModelBundleStore(Protocol):
    """Persist and load opaque fitted model artifacts with external metadata."""

    def persist(
        self,
        *,
        pipeline: object,
        profile: ModelProfile,
        evaluation: ProfileEvaluation,
        feature_set: FeatureSet,
        feature_contract_sha256: str,
        provenance: dict[str, str],
        output_dir: Path,
    ) -> tuple[Path, Path]:
        """Write one model bundle and return its model and metadata paths."""

    def load(self, model_path: Path, metadata_path: Path) -> object:
        """Load one model only when its persisted integrity contract is valid."""

    def digest(self, path: Path) -> str:
        """Return the immutable content digest for one persisted bundle artifact."""


class SourceRevisionControl(Protocol):
    """Resolve and verify the source identity used by a model release."""

    def capture(self) -> str:
        """Return the current Git object ID without requiring a clean worktree."""

    def capture_clean(self) -> str:
        """Return the current Git object ID only from a clean worktree."""

    def verify(self, frozen_commit: str) -> None:
        """Reject a dirty or source-changed tree relative to one frozen commit."""


class CanonicalEvidenceGuard(Protocol):
    """Prevent mutation of a revision whose sealed test was already finalized."""

    def assert_not_finalized(self, configuration: ModelTrainerConfiguration) -> None:
        """Raise when canonical evidence records a completed sealed test."""


class ReleaseProvenance(Protocol):
    """Persist and verify DVC, Git, config, bundle, and release evidence boundaries."""

    def assert_not_frozen(self, configuration: ModelTrainerConfiguration) -> None:
        """Reject a workflow that would modify already frozen release inputs."""

    def model_provenance(
        self, configuration: ModelTrainerConfiguration, source_commit: str
    ) -> dict[str, str]:
        """Return train/valid model lineage for MLflow and bundle metadata."""

    def tracking_provenance(
        self,
        configuration: ModelTrainerConfiguration,
        source_commit: str,
        *,
        roles: tuple[str, ...],
    ) -> dict[str, str]:
        """Return provenance only for roles consumed by one benchmark stage."""

    def write_freeze(
        self,
        configuration: ModelTrainerConfiguration,
        *,
        source_commit: str,
        bundles: tuple[FrozenModelBundle, ...],
        decisions: tuple[ReleaseDecision, ...],
    ) -> Path:
        """Write one immutable pre-test freeze after all bundles are constructed."""

    def verify_freeze(self, configuration: ModelTrainerConfiguration) -> FrozenRelease:
        """Verify pre-test inputs and return the frozen source and bundles."""

    def write_release_manifest(
        self,
        configuration: ModelTrainerConfiguration,
        *,
        final_evidence_path: Path,
        canonical_evidence_path: Path,
        bundles: tuple[FrozenModelBundle, ...],
        decisions: tuple[ReleaseDecision, ...],
        final_mlflow_run_ids: dict[str, str],
        approved_profile: str | None,
    ) -> Path:
        """Write a post-test release document without mutating the pre-test freeze."""

    def write_canonical_evidence(
        self,
        configuration: ModelTrainerConfiguration,
        *,
        final_evidence_path: Path,
        accessed_roles: tuple[str, ...],
        profiles: object,
        decisions: tuple[ReleaseDecision, ...],
        deployment_allowed: bool,
    ) -> Path:
        """Write canonical sealed-test evidence before the release manifest exists."""

    def configuration_digests(
        self, configuration: ModelTrainerConfiguration
    ) -> dict[str, str]:
        """Return the frozen versioned configuration digest mapping."""
