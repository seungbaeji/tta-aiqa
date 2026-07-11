"""Frozen release manifest and model bundle persistence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
from aiqa_model.domain import BenchmarkResult
from aiqa_qa.domain import ReleaseDecision
from sklearn.pipeline import Pipeline

from model_trainer.release import decisions_to_dict
from model_trainer.settings import ModelTrainerSettings

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
    settings: ModelTrainerSettings,
    development_evidence_path: Path,
    decisions: tuple[ReleaseDecision, ...],
) -> Path:
    paths = {name: Path(getattr(settings, name)) for name in FROZEN_INPUTS}
    paths.update(
        {
            "train_dataset": settings.split_dataset_dir / "train.csv",
            "valid_dataset": settings.split_dataset_dir / "valid.csv",
            "development_evidence": development_evidence_path,
        }
    )
    paths.update(
        {name: Path(getattr(settings, name)) for name in REVISION_FROZEN_INPUTS}
    )
    if settings.feature_diagnostics_path.exists():
        paths["feature_diagnostics"] = settings.feature_diagnostics_path
    document = {
        "schema_version": 2,
        "sealed_test_status": "not_accessed",
        "sha256": {name: sha256(path) for name, path in paths.items()},
        "development_decisions": decisions_to_dict(decisions),
    }
    return write_json(document, settings.freeze_manifest_path)


def verify_freeze_manifest(settings: ModelTrainerSettings) -> dict[str, object]:
    document = json.loads(settings.freeze_manifest_path.read_text(encoding="utf-8"))
    paths = {name: Path(getattr(settings, name)) for name in FROZEN_INPUTS}
    paths.update(
        {
            "train_dataset": settings.split_dataset_dir / "train.csv",
            "valid_dataset": settings.split_dataset_dir / "valid.csv",
            "development_evidence": settings.development_evidence_path,
        }
    )
    if document.get("schema_version", 1) >= 2:
        paths.update(
            {name: Path(getattr(settings, name)) for name in REVISION_FROZEN_INPUTS}
        )
        if "feature_diagnostics" in document.get("sha256", {}):
            paths["feature_diagnostics"] = settings.feature_diagnostics_path
    actual = {name: sha256(path) for name, path in paths.items()}
    if actual != document.get("sha256"):
        raise RuntimeError("frozen model inputs changed before sealed test evaluation")
    return document


def persist_bundles(
    bundles: dict[str, Pipeline],
    result: BenchmarkResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    evaluations = {item.profile: item for item in result.profiles}
    outputs: list[Path] = []
    for profile, pipeline in sorted(bundles.items()):
        model_path = output_dir / profile / "model.joblib"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, model_path)
        evaluation = evaluations[profile]
        write_json(
            {
                "schema_version": 1,
                "profile": profile,
                "threshold": evaluation.threshold,
                "model_sha256": sha256(model_path),
            },
            model_path.with_name("metadata.json"),
        )
        outputs.append(model_path)
    return tuple(outputs)


def finalize_manifest(
    settings: ModelTrainerSettings,
    final_evidence_path: Path,
    decisions: tuple[ReleaseDecision, ...],
    bundle_paths: tuple[Path, ...],
    release_status: str,
) -> Path:
    document = json.loads(settings.freeze_manifest_path.read_text(encoding="utf-8"))
    document.update(
        {
            "sealed_test_status": "evaluated_once",
            "release_status": release_status,
            "sealed_test_sha256": sha256(settings.split_dataset_dir / "test.csv"),
            "final_evidence_sha256": sha256(final_evidence_path),
            "final_decisions": decisions_to_dict(decisions),
            "model_bundles": {
                str(artifact.relative_to(settings.model_bundle_dir)): sha256(artifact)
                for path in bundle_paths
                for artifact in (path, path.with_name("metadata.json"))
            },
        }
    )
    return write_json(document, settings.freeze_manifest_path)


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
