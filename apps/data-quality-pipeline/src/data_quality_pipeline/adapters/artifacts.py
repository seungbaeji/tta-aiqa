"""CSV dataset artifact adapter owned by the Data Quality Pipeline process."""

from dataclasses import dataclass
from pathlib import Path

from aiqa_data.adapters import (
    read_dataset_csv,
    read_split_csv,
    write_dataset_csv,
    write_role_datasets,
    write_split_csv,
)
from aiqa_data.application import PreparedPatientFeatures, PreparedSplitManifest


@dataclass(frozen=True)
class CsvDatasetArtifactStore:
    """Persist and load deterministic CSV artifacts through aiqa-data adapters."""

    def read_features(self, path: Path) -> PreparedPatientFeatures:
        """Load one canonical patient-feature CSV artifact."""
        return read_dataset_csv(path)

    def read_split_manifest(self, path: Path) -> PreparedSplitManifest:
        """Load one deterministic patient-to-role split manifest."""
        return read_split_csv(path)

    def write_features(self, dataset: PreparedPatientFeatures, path: Path) -> None:
        """Persist one canonical patient-feature CSV artifact."""
        write_dataset_csv(dataset, path)

    def write_split_manifest(self, manifest: PreparedSplitManifest, path: Path) -> None:
        """Persist one deterministic patient-to-role split manifest."""
        write_split_csv(manifest, path)

    def write_role_datasets(
        self,
        features: PreparedPatientFeatures,
        manifest: PreparedSplitManifest,
        output_dir: Path,
    ) -> None:
        """Persist role-specific datasets and remove operational labels."""
        write_role_datasets(features, manifest, output_dir)
