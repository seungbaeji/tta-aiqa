"""Model Trainer release provenance contract tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from aiqa_qa.domain import Decision, ReleaseCheck, ReleaseDecision
from model_trainer.adapters.release_provenance import (
    FrozenModelBundle,
    verify_release_freeze,
    write_release_freeze,
    write_release_manifest,
)
from model_trainer.adapters.source_control import GitRevision
from model_trainer.domain import ModelTrainerConfiguration


def sha256(path: Path) -> str:
    """Return the SHA-256 digest used by the persisted provenance documents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, content: str) -> Path:
    """Create one deterministic text fixture below the temporary workspace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def configuration(tmp_path: Path) -> ModelTrainerConfiguration:
    """Create a self-contained new-revision Model Trainer configuration."""
    dataset_dir = tmp_path / "data" / "datasets"
    write(dataset_dir / "train.csv", "record_id,target\n1,0\n")
    write(dataset_dir / "valid.csv", "record_id,target\n2,1\n")
    write(dataset_dir / "test.csv", "record_id,target\n3,1\n")

    feature_contract = write(tmp_path / "configs" / "feature.yaml", "name: vital\n")
    feature_sets = write(tmp_path / "configs" / "feature-sets.yaml", "sets: []\n")
    profiles = write(tmp_path / "configs" / "profiles.yaml", "profiles: []\n")
    evaluation = write(tmp_path / "configs" / "evaluation.yaml", "schema_version: 1\n")
    release_policy = write(tmp_path / "configs" / "release.yaml", "name: policy\n")
    dvc_lock = write(tmp_path / "dvc.lock", "stages: {}\n")
    data_manifest = tmp_path / "evidence" / "data-lineage.json"
    write(
        data_manifest,
        json.dumps(
            {
                "schema_version": 1,
                "revision": "v3",
                "source": {"archive_sha256": "archive-digest"},
                "configuration": {"dvc_lock_sha256": sha256(dvc_lock)},
                "role_datasets": {
                    role: {
                        "path": str(dataset_dir / f"{role}.csv"),
                        "sha256": sha256(dataset_dir / f"{role}.csv"),
                    }
                    for role in ("train", "valid", "test")
                },
            }
        )
        + "\n",
    )
    development = write(tmp_path / "evidence" / "development.json", "{}\n")
    return ModelTrainerConfiguration(
        repository_root=tmp_path,
        feature_contract_path=feature_contract,
        feature_sets_path=feature_sets,
        profiles_path=profiles,
        evaluation_path=evaluation,
        release_policy_path=release_policy,
        split_dataset_dir=dataset_dir,
        split_config_path=tmp_path / "params.yaml",
        data_manifest_path=data_manifest,
        mlflow_tracking_uri="sqlite:///mlflow.db",
        mlflow_experiment_name="test",
        dvc_lock_path=dvc_lock,
        artifact_dir=tmp_path / "artifacts",
        development_evidence_path=development,
        feature_diagnostics_path=tmp_path / "evidence" / "diagnostics.json",
        model_bundle_dir=tmp_path / "models",
        deployed_model_dir=tmp_path / "deployed",
        bootstrap_manifest_path=tmp_path / "artifacts" / "bootstrap.json",
        bootstrap_evidence_path=tmp_path / "evidence" / "bootstrap.json",
        freeze_manifest_path=tmp_path / "evidence" / "release-freeze.json",
        release_manifest_path=tmp_path / "evidence" / "release-manifest.json",
        canonical_evidence_path=tmp_path / "evidence" / "canonical.json",
    )


def release_decisions() -> tuple[ReleaseDecision, ReleaseDecision]:
    """Return the course's held Candidate A and approved Candidate B outcome."""
    checks = tuple((check, True) for check in ReleaseCheck)
    return (
        ReleaseDecision(
            profile="candidate-a",
            decision=Decision.HOLD,
            checks=((ReleaseCheck.RECALL_GUARDRAIL, False), *checks[1:]),
        ),
        ReleaseDecision(
            profile="candidate-b",
            decision=Decision.APPROVE,
            checks=checks,
        ),
    )


def frozen_bundles(
    configuration: ModelTrainerConfiguration,
) -> tuple[FrozenModelBundle, ...]:
    """Write two serialized model fixtures and return their immutable references."""
    bundles: list[FrozenModelBundle] = []
    for profile in ("candidate-a", "candidate-b"):
        directory = configuration.model_bundle_dir / profile
        model = write(directory / "model.joblib", f"{profile}-model")
        metadata = write(
            directory / "metadata.json",
            f"{{\"profile\": \"{profile}\"}}\n",
        )
        bundles.append(
            FrozenModelBundle(
                profile=profile,
                model_path=model,
                metadata_path=metadata,
                mlflow_run_id=f"model-run-{profile}",
            )
        )
    return tuple(bundles)


def test_release_freeze_binds_git_data_config_and_bundle_identity(
    tmp_path: Path,
) -> None:
    """A pre-test freeze owns immutable cross-boundary references, not source files."""
    config = configuration(tmp_path)
    bundles = frozen_bundles(config)

    path = write_release_freeze(
        config,
        source_revision=GitRevision(commit="a" * 40),
        bundles=bundles,
        decisions=release_decisions(),
    )

    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["schema_version"] == 3
    assert document["source"]["git_commit"] == "a" * 40
    assert document["data"]["revision"] == "v3"
    assert document["sealed_test"]["sha256"] == sha256(
        config.split_dataset_dir / "test.csv"
    )
    assert {item["profile"] for item in document["model_bundles"]} == {
        "candidate-a",
        "candidate-b",
    }
    assert "implementation_path" not in json.dumps(document)
    assert "source_file" not in json.dumps(document)


def test_freeze_verification_rejects_changed_versioned_input(tmp_path: Path) -> None:
    """Finalization must stop before test access when a frozen input changes."""
    config = configuration(tmp_path)
    write_release_freeze(
        config,
        source_revision=GitRevision(commit="b" * 40),
        bundles=frozen_bundles(config),
        decisions=release_decisions(),
    )
    write(config.evaluation_path, "schema_version: 2\n")

    with pytest.raises(RuntimeError, match="frozen model inputs changed"):
        verify_release_freeze(config)


def test_release_manifest_is_separate_from_immutable_freeze(tmp_path: Path) -> None:
    """Post-test release output links a freeze digest without rewriting the freeze."""
    config = configuration(tmp_path)
    bundles = frozen_bundles(config)
    freeze = write_release_freeze(
        config,
        source_revision=GitRevision(commit="c" * 40),
        bundles=bundles,
        decisions=release_decisions(),
    )
    frozen_bytes = freeze.read_bytes()
    final = write(config.artifact_dir / "final.json", "{}\n")
    canonical = write(config.canonical_evidence_path, "{}\n")

    manifest = write_release_manifest(
        config,
        final_evidence_path=final,
        canonical_evidence_path=canonical,
        bundles=bundles,
        decisions=release_decisions(),
        final_mlflow_run_ids={
            "candidate-a": "final-run-a",
            "candidate-b": "final-run-b",
        },
        approved_profile="candidate-b",
    )

    document = json.loads(manifest.read_text(encoding="utf-8"))
    assert freeze.read_bytes() == frozen_bytes
    assert document["freeze_manifest"]["sha256"] == sha256(freeze)
    assert document["approved_model"]["profile"] == "candidate-b"
    assert document["approved_model"]["model_mlflow_run_id"] == "model-run-candidate-b"
    assert document["approved_model"]["final_mlflow_run_id"] == "final-run-b"
