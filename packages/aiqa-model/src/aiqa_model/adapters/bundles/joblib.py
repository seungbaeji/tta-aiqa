"""Joblib persistence for immutable sklearn model bundles."""

from __future__ import annotations

from pathlib import Path

import joblib
from aiqa_core.domain import FeatureSet
from sklearn.pipeline import Pipeline

from aiqa_model.adapters.bundles.metadata import ModelBundleMetadataDocument
from aiqa_model.adapters.checksum import sha256_file
from aiqa_model.domain import ModelProfile, ProfileEvaluation


def persist_model_bundle(
    *,
    pipeline: Pipeline,
    profile: ModelProfile,
    evaluation: ProfileEvaluation,
    feature_set: FeatureSet,
    feature_contract_sha256: str,
    provenance: dict[str, str],
    output_dir: Path,
) -> tuple[Path, Path]:
    """Persist one fitted pipeline with matching embedded and external metadata."""
    profile_dir = output_dir / profile.name
    profile_dir.mkdir(parents=True, exist_ok=True)
    model_path = profile_dir / "model.joblib"
    metadata_path = profile_dir / "metadata.json"
    metadata = ModelBundleMetadataDocument.from_domain(
        profile=profile,
        evaluation=evaluation,
        feature_set=feature_set,
        feature_contract_sha256=feature_contract_sha256,
        provenance=provenance,
    )
    joblib.dump(
        {
            "model": pipeline,
            "metadata": metadata.embedded_document().model_dump(
                mode="json", exclude_none=True
            ),
        },
        model_path,
    )
    external_metadata = metadata.model_copy(
        update={"model_sha256": sha256_file(model_path)}
    )
    metadata_path.write_text(
        external_metadata.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return model_path, metadata_path


def load_model_bundle(model_path: Path, metadata_path: Path) -> Pipeline:
    """Load a bundle only when its embedded and external metadata are identical."""
    metadata = ModelBundleMetadataDocument.model_validate_json(
        metadata_path.read_text(encoding="utf-8")
    )
    if metadata.model_sha256 != sha256_file(model_path):
        raise ValueError("model bundle checksum does not match metadata")
    bundle = joblib.load(model_path)
    if not isinstance(bundle, dict) or set(bundle) != {"model", "metadata"}:
        raise ValueError("model bundle payload is invalid")
    embedded = ModelBundleMetadataDocument.model_validate(bundle["metadata"])
    if embedded != metadata.embedded_document():
        raise ValueError("model bundle metadata does not match embedded metadata")
    model = bundle["model"]
    if not isinstance(model, Pipeline):
        raise ValueError("model bundle does not contain a sklearn Pipeline")
    return model
