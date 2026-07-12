"""Frozen release manifest persistence and provenance hashing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aiqa_qa.domain import ReleaseDecision

from model_trainer.release import decisions_to_dict
from model_trainer.workflow import ModelTrainerConfiguration

FROZEN_INPUTS = (
    "feature_contract_path",
    "feature_sets_path",
    "profiles_path",
    "evaluation_path",
    "release_policy_path",
)
REVISION_FROZEN_INPUTS = (
    "data_manifest_path",
    "dvc_lock_path",
    "model_implementation_path",
    "release_implementation_path",
    "trainer_implementation_path",
    "tracking_implementation_path",
)


def write_freeze_manifest(
    configuration: ModelTrainerConfiguration,
    development_evidence_path: Path,
    decisions: tuple[ReleaseDecision, ...],
) -> Path:
    paths = {name: Path(getattr(configuration, name)) for name in FROZEN_INPUTS}
    paths.update(
        {
            "train_dataset": configuration.split_dataset_dir / "train.csv",
            "valid_dataset": configuration.split_dataset_dir / "valid.csv",
            "development_evidence": development_evidence_path,
        }
    )
    paths.update(
        {
            name: Path(getattr(configuration, name))
            for name in REVISION_FROZEN_INPUTS
        }
    )
    if configuration.feature_diagnostics_path.exists():
        paths["feature_diagnostics"] = configuration.feature_diagnostics_path
    document = {
        "schema_version": 2,
        "sealed_test_status": "not_accessed",
        "sha256": {name: sha256(path) for name, path in paths.items()},
        "development_decisions": decisions_to_dict(decisions),
    }
    return write_json(document, configuration.freeze_manifest_path)


def verify_freeze_manifest(
    configuration: ModelTrainerConfiguration,
) -> dict[str, object]:
    document = json.loads(
        configuration.freeze_manifest_path.read_text(encoding="utf-8")
    )
    paths = {name: Path(getattr(configuration, name)) for name in FROZEN_INPUTS}
    paths.update(
        {
            "train_dataset": configuration.split_dataset_dir / "train.csv",
            "valid_dataset": configuration.split_dataset_dir / "valid.csv",
            "development_evidence": configuration.development_evidence_path,
        }
    )
    if document.get("schema_version", 1) >= 2:
        paths.update(
            {
                name: Path(getattr(configuration, name))
                for name in REVISION_FROZEN_INPUTS
            }
        )
        if "feature_diagnostics" in document.get("sha256", {}):
            paths["feature_diagnostics"] = configuration.feature_diagnostics_path
    actual = {name: sha256(path) for name, path in paths.items()}
    if actual != document.get("sha256"):
        raise RuntimeError("frozen model inputs changed before sealed test evaluation")
    return document


def finalize_manifest(
    configuration: ModelTrainerConfiguration,
    final_evidence_path: Path,
    decisions: tuple[ReleaseDecision, ...],
    bundle_paths: tuple[Path, ...],
    release_status: str,
) -> Path:
    document = json.loads(
        configuration.freeze_manifest_path.read_text(encoding="utf-8")
    )
    document.update(
        {
            "sealed_test_status": "evaluated_once",
            "release_status": release_status,
            "sealed_test_sha256": sha256(
                configuration.split_dataset_dir / "test.csv"
            ),
            "final_evidence_sha256": sha256(final_evidence_path),
            "final_decisions": decisions_to_dict(decisions),
            "model_bundles": {
                str(artifact.relative_to(configuration.model_bundle_dir)): sha256(
                    artifact
                )
                for path in bundle_paths
                for artifact in (path, path.with_name("metadata.json"))
            },
        }
    )
    return write_json(document, configuration.freeze_manifest_path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(document: dict[str, object], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path
