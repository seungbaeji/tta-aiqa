"""Immutable sklearn model bundle adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
from aiqa_core.domain import FeatureSet
from sklearn.pipeline import Pipeline

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
    profile_dir = output_dir / profile.name
    profile_dir.mkdir(parents=True, exist_ok=True)
    model_path = profile_dir / "model.joblib"
    metadata_path = profile_dir / "metadata.json"
    metadata = {
        "schema_version": 1,
        "profile": profile.name,
        "candidate_id": profile.candidate_id,
        "model_role": profile.model_role.value,
        "model_kind": profile.kind.value,
        "threshold": profile.threshold,
        "params": profile.parameter_dict(),
        "target": feature_set.target,
        "feature_contract": {
            "name": feature_set.name,
            "sha256": feature_contract_sha256,
            "features": [
                {
                    "name": feature.name,
                    "dtype": feature.dtype.value,
                    "nullable": feature.nullable,
                }
                for feature in feature_set.features
            ],
        },
        "validation_metrics": {
            "precision": evaluation.metrics.precision,
            "recall": evaluation.metrics.recall,
            "f1": evaluation.metrics.f1,
            "roc_auc": evaluation.metrics.roc_auc,
            "pr_auc": evaluation.metrics.pr_auc,
            "false_negative": evaluation.metrics.false_negative,
            "bootstrap_recall_lower": evaluation.bootstrap_recall_lower,
        },
        "provenance": provenance,
    }
    joblib.dump({"model": pipeline, "metadata": metadata}, model_path)
    metadata["model_sha256"] = _sha256(model_path)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return model_path, metadata_path


def load_model_bundle(model_path: Path, metadata_path: Path) -> Pipeline:
    """Load a bundle only when its external and embedded metadata agree."""
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_hash = metadata.get("model_sha256")
    if expected_hash != _sha256(model_path):
        raise ValueError("model bundle checksum does not match metadata")
    bundle = joblib.load(model_path)
    if not isinstance(bundle, dict) or set(bundle) != {"model", "metadata"}:
        raise ValueError("model bundle payload is invalid")
    embedded = bundle["metadata"]
    comparable = {
        key: value for key, value in metadata.items() if key != "model_sha256"
    }
    if embedded != comparable:
        raise ValueError("model bundle metadata does not match embedded metadata")
    model = bundle["model"]
    if not isinstance(model, Pipeline):
        raise ValueError("model bundle does not contain a sklearn Pipeline")
    return model


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
