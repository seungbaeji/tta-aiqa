"""Focused external capabilities for the Data Quality Pipeline process."""

from pathlib import Path
from typing import Protocol

from aiqa_data.application import PreparedPatientFeatures, PreparedSplitManifest
from aiqa_data.domain import SourceIntegrityReport


class SourceGateway(Protocol):
    """Verify, extract, and persist evidence for the configured official source."""

    def verify(self) -> SourceIntegrityReport:
        """Return typed evidence that every expected source file is intact."""

    def write_evidence(self, report: SourceIntegrityReport, path: Path) -> None:
        """Persist source integrity evidence at the requested artifact path."""

    def extract(self) -> None:
        """Extract the verified raw archive into its configured records directory."""


class DatasetArtifactStore(Protocol):
    """Read and write deterministic dataset, split, and role CSV artifacts."""

    def read_features(self, path: Path) -> PreparedPatientFeatures:
        """Load one canonical patient-feature CSV artifact."""

    def read_split_manifest(self, path: Path) -> PreparedSplitManifest:
        """Load one deterministic patient-to-role split manifest."""

    def write_features(self, dataset: PreparedPatientFeatures, path: Path) -> None:
        """Persist one canonical patient-feature CSV artifact."""

    def write_split_manifest(self, manifest: PreparedSplitManifest, path: Path) -> None:
        """Persist one deterministic patient-to-role split manifest."""

    def write_role_datasets(
        self,
        features: PreparedPatientFeatures,
        manifest: PreparedSplitManifest,
        output_dir: Path,
    ) -> None:
        """Write role-specific datasets with operational labels removed."""


class QualityValidator(Protocol):
    """Run configured quality checks and persist their runtime evidence."""

    def validate(self, patient_features_path: Path, artifact_dir: Path) -> bool:
        """Return whether raw and processed quality evidence both passed."""
