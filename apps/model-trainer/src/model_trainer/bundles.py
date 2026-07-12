"""Frozen model-bundle construction and baseline publication workflows."""

import json
import shutil
import subprocess
from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_data.adapters import load_split_config
from aiqa_model.adapters import (
    MlflowModelTracker,
    benchmark_from_dict,
    load_profiles,
    persist_model_bundle,
)
from aiqa_model.application import fit_model_bundles

from model_trainer.development import build_benchmark
from model_trainer.provenance import sha256, verify_freeze_manifest, write_json
from model_trainer.release import assert_teaching_scenario, evaluate_release
from model_trainer.workflow import ModelTrainerConfiguration


def bootstrap_models(configuration: ModelTrainerConfiguration) -> Path:
    """Fit frozen train/valid bundles and publish only the baseline model."""
    if configuration.bootstrap_manifest_path.exists():
        raise RuntimeError("model bootstrap evidence already exists")
    verify_freeze_manifest(configuration)
    development = benchmark_from_dict(
        json.loads(
            configuration.development_evidence_path.read_text(encoding="utf-8")
        )
    )
    if development.evaluation_role != "valid" or development.accessed_roles != (
        "train",
        "valid",
    ):
        raise ValueError("development evidence has an invalid role contract")
    decisions = evaluate_release(configuration, development)
    assert_teaching_scenario(decisions)

    benchmark = build_benchmark(configuration)
    _, profiles = load_profiles(configuration.profiles_path)
    pipelines = fit_model_bundles(
        benchmark=benchmark,
        profiles=tuple(profile.name for profile in profiles),
    )
    evaluations = {item.profile: item for item in development.profiles}
    feature_set = load_feature_contract(configuration.feature_contract_path)
    provenance = model_provenance(configuration)
    tracker = MlflowModelTracker(
        configuration.mlflow_tracking_uri,
        configuration.mlflow_experiment_name,
    )

    bundles: dict[str, dict[str, object]] = {}
    for profile in profiles:
        model_path, metadata_path = persist_model_bundle(
            pipeline=pipelines.get(profile.name),
            profile=profile,
            evaluation=evaluations[profile.name],
            feature_set=feature_set,
            feature_contract_sha256=sha256(configuration.feature_contract_path),
            provenance=provenance,
            output_dir=configuration.model_bundle_dir,
        )
        run_id = tracker.record(
            profile=profile,
            evaluation=evaluations[profile.name],
            pipeline=pipelines.get(profile.name),
            bundle_dir=model_path.parent,
            train_path=configuration.split_dataset_dir / "train.csv",
            valid_path=configuration.split_dataset_dir / "valid.csv",
            provenance=provenance,
        )
        bundles[profile.name] = {
            "model_path": str(model_path),
            "model_sha256": sha256(model_path),
            "metadata_path": str(metadata_path),
            "metadata_sha256": sha256(metadata_path),
            "mlflow_run_id": run_id,
            "deployed": profile.name == "baseline",
        }

    publish_baseline(configuration)
    document: dict[str, object] = {
        "schema_version": 1,
        "evaluation_role": "valid",
        "accessed_roles": ["train", "valid"],
        "bundles": bundles,
        "initial_deployed_profile": "baseline",
        "candidate_deployment_allowed": False,
        "candidate_deployment_reason": candidate_deployment_reason(configuration),
        "provenance": provenance,
    }
    write_json(
        portable_bootstrap_document(document), configuration.bootstrap_evidence_path
    )
    return write_json(document, configuration.bootstrap_manifest_path)


def reconcile_bootstrap_evidence(configuration: ModelTrainerConfiguration) -> Path:
    """Regenerate portable bootstrap evidence from the immutable local manifest."""
    document = json.loads(
        configuration.bootstrap_manifest_path.read_text(encoding="utf-8")
    )
    return write_json(
        portable_bootstrap_document(document), configuration.bootstrap_evidence_path
    )


def model_provenance(configuration: ModelTrainerConfiguration) -> dict[str, str]:
    """Collect versioned code, data, and configuration lineage for model bundles."""
    data_manifest = json.loads(
        configuration.data_manifest_path.read_text(encoding="utf-8")
    )
    role_datasets = data_manifest["role_datasets"]
    split_seed = data_manifest.get("configuration", {}).get("split_seed")
    if split_seed is None:
        split_seed = load_split_config(configuration.split_config_path).random_seed
    return {
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "git_worktree_dirty": str(
            bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], text=True
                )
            )
        ).lower(),
        "dvc_lock_revision": sha256(configuration.dvc_lock_path),
        "raw_data_hash": data_manifest["source"]["archive_sha256"],
        "train_data_hash": role_datasets["train"]["sha256"],
        "valid_data_hash": role_datasets["valid"]["sha256"],
        "test_data_hash": role_datasets["test"]["sha256"],
        "split_seed": str(split_seed),
        "data_revision": str(data_manifest.get("revision", "v1")),
        "model_input_config_hash": sha256(configuration.feature_contract_path),
        "model_profile_config_hash": sha256(configuration.profiles_path),
        "evaluation_config_hash": sha256(configuration.evaluation_path),
        "release_policy_config_hash": sha256(configuration.release_policy_path),
    }


def publish_baseline(configuration: ModelTrainerConfiguration) -> None:
    """Copy the baseline bundle into the deployed-model location."""
    source = configuration.model_bundle_dir / "baseline"
    configuration.deployed_model_dir.mkdir(parents=True, exist_ok=True)
    for name in ("model.joblib", "metadata.json"):
        shutil.copy2(source / name, configuration.deployed_model_dir / name)
    write_json(
        {
            "schema_version": 1,
            "profile": "baseline",
            "model_sha256": sha256(
                configuration.deployed_model_dir / "model.joblib"
            ),
            "candidate_deployment_allowed": False,
        },
        configuration.deployed_model_dir / "deployment.json",
    )


def candidate_deployment_reason(configuration: ModelTrainerConfiguration) -> str:
    """Explain why bootstrap does not deploy a candidate model."""
    if not configuration.canonical_evidence_path.exists():
        return "awaiting_sealed_test"
    document = json.loads(
        configuration.canonical_evidence_path.read_text(encoding="utf-8")
    )
    if document.get("deployment_allowed") is True:
        return "approved_but_not_published_by_bootstrap"
    return "sealed_test_scenario_review"


def portable_bootstrap_document(document: dict[str, object]) -> dict[str, object]:
    """Replace local bundle paths with workspace-relative evidence paths."""
    portable = json.loads(json.dumps(document))
    bundles = portable.get("bundles", {})
    for item in bundles.values():
        for key in ("model_path", "metadata_path"):
            path = Path(item[key])
            try:
                item[key] = str(path.relative_to(Path.cwd()))
            except ValueError:
                raise ValueError(
                    f"bootstrap artifact is outside the workspace: {path}"
                ) from None
    return portable
