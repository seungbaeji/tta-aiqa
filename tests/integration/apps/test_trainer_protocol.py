"""Canonical model workflow protocol tests."""

import json
from pathlib import Path

import pytest
from model_trainer.bootstrap import bootstrap
from model_trainer.domain import TrainerCommand, TrainerStage
from model_trainer.settings import ModelTrainerSettings

ROOT = Path(__file__).resolve().parents[3]


def finalized_settings(tmp_path: Path) -> ModelTrainerSettings:
    canonical = tmp_path / "canonical.json"
    canonical.write_text(
        json.dumps({"sealed_test": {"status": "evaluated_once"}}),
        encoding="utf-8",
    )
    return ModelTrainerSettings(
        _env_file=None,
        repository_root=ROOT,
        feature_contract_path=ROOT / "configs/contracts/model-input.yaml",
        feature_sets_path=ROOT / "configs/model/revisions/v2/feature-sets.yaml",
        profiles_path=ROOT / "configs/model/revisions/v2/profiles.yaml",
        evaluation_path=ROOT / "configs/model/revisions/v2/evaluation.yaml",
        release_policy_path=ROOT / "configs/qa/revisions/v2.yaml",
        split_dataset_dir=tmp_path / "datasets",
        mlflow_tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}",
        artifact_dir=tmp_path / "artifacts",
        model_bundle_dir=tmp_path / "models",
        freeze_manifest_path=tmp_path / "freeze.json",
        release_manifest_path=tmp_path / "release.json",
        canonical_evidence_path=canonical,
    )


def test_finalized_canonical_evidence_blocks_development_and_final(
    tmp_path: Path,
) -> None:
    settings = finalized_settings(tmp_path)
    runtime = bootstrap(settings)

    try:
        with pytest.raises(RuntimeError, match="already evaluated"):
            runtime.run(TrainerCommand(TrainerStage.DEVELOPMENT))
        with pytest.raises(RuntimeError, match="already evaluated"):
            runtime.run(
                TrainerCommand(
                    TrainerStage.FINAL,
                    sealed_test_token="CONFIRM-FROZEN-CANONICAL-TEST",
                )
            )
    finally:
        runtime.telemetry.shutdown()
