"""Joblib-backed model bundle adapter for the Model Trainer process."""

from dataclasses import dataclass
from pathlib import Path

from aiqa_core.domain import FeatureSet
from aiqa_model.adapters import load_model_bundle, persist_model_bundle
from aiqa_model.adapters.checksum import sha256_file
from aiqa_model.domain import ModelProfile, ProfileEvaluation


@dataclass(frozen=True)
class JoblibModelBundleStore:
    """Persist and load opaque model bundles through aiqa-model's integrity adapter."""

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
        """Write one sklearn-backed model artifact and matching external metadata."""
        return persist_model_bundle(
            pipeline=pipeline,
            profile=profile,
            evaluation=evaluation,
            feature_set=feature_set,
            feature_contract_sha256=feature_contract_sha256,
            provenance=provenance,
            output_dir=output_dir,
        )

    def load(self, model_path: Path, metadata_path: Path) -> object:
        """Load one bundle only after package-level integrity verification."""
        return load_model_bundle(model_path, metadata_path)

    def digest(self, path: Path) -> str:
        """Return the package-owned SHA-256 identity of one model bundle artifact."""
        return sha256_file(path)
