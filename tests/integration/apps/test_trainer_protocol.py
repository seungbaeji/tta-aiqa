"""Canonical model workflow protocol tests."""

import json
from pathlib import Path

import pytest
from model_trainer.bootstrap import bootstrap
from model_trainer.settings import ModelTrainerSettings
from model_trainer.workflow import TrainerCommand, TrainerStage


def finalized_settings(tmp_path: Path) -> ModelTrainerSettings:
    canonical = tmp_path / "canonical.json"
    canonical.write_text(
        json.dumps({"sealed_test": {"status": "evaluated_once"}}),
        encoding="utf-8",
    )
    return ModelTrainerSettings(
        _env_file=None,
        feature_contract_path=tmp_path / "feature.yaml",
        feature_sets_path=tmp_path / "feature-sets.yaml",
        profiles_path=tmp_path / "profiles.yaml",
        evaluation_path=tmp_path / "evaluation.yaml",
        release_policy_path=tmp_path / "release.yaml",
        split_dataset_dir=tmp_path / "datasets",
        mlflow_tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}",
        artifact_dir=tmp_path / "artifacts",
        model_bundle_dir=tmp_path / "models",
        freeze_manifest_path=tmp_path / "freeze.json",
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
