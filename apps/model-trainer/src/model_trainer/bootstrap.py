"""Composition root for the Model Trainer."""

import json
import shutil
import subprocess
from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_data.adapters import load_split_config
from aiqa_model.adapters import (
    MlflowBenchmarkTracker,
    MlflowModelTracker,
    SklearnBenchmark,
    benchmark_from_dict,
    benchmark_to_dict,
    feature_diagnostics_to_dict,
    load_evaluation_plan,
    load_model_bundle,
    load_profiles,
    persist_model_bundle,
)
from aiqa_model.application import (
    ConfirmFrozenModels,
    DevelopModels,
    DiagnoseFeatures,
    FitModelBundles,
)
from aiqa_model.domain import BenchmarkResult
from aiqa_model.ports import FittedModels
from aiqa_qa.adapters import load_release_policy
from aiqa_qa.domain import ReleaseDecision

from model_trainer.provenance import (
    finalize_manifest,
    sha256,
    verify_freeze_manifest,
    write_freeze_manifest,
    write_json,
)
from model_trainer.release import (
    assert_teaching_scenario,
    decisions_to_dict,
    evaluate_release,
    teaching_scenario_matches,
)
from model_trainer.settings import ModelTrainerSettings


def build_benchmark(settings: ModelTrainerSettings) -> SklearnBenchmark:
    feature_set = load_feature_contract(settings.feature_contract_path)
    random_seed, profiles = load_profiles(settings.profiles_path)
    evaluation = load_evaluation_plan(settings.evaluation_path)
    return SklearnBenchmark(
        settings.split_dataset_dir,
        feature_set,
        profiles,
        evaluation,
        random_seed,
    )


def run_development(settings: ModelTrainerSettings) -> Path:
    _assert_canonical_test_not_finalized(settings)
    result = DevelopModels(build_benchmark(settings)).execute()
    output = write_json(
        benchmark_to_dict(result), settings.artifact_dir / "development-benchmark.json"
    )
    write_json(benchmark_to_dict(result), settings.development_evidence_path)
    decisions = evaluate_release(settings, result)
    assert_teaching_scenario(decisions)
    write_json(
        {
            "schema_version": 1,
            "evaluation_role": "valid",
            "decisions": decisions_to_dict(decisions),
        },
        settings.artifact_dir / "development-release-decisions.json",
    )
    _track_benchmark(settings, result, output)
    write_freeze_manifest(settings, settings.development_evidence_path, decisions)
    return output


def run_feature_diagnostics(settings: ModelTrainerSettings) -> Path:
    manifest = verify_freeze_manifest(settings)
    policy_document, _ = load_release_policy(settings.release_policy_path)
    diagnostics = DiagnoseFeatures(build_benchmark(settings)).execute(
        baseline_profile=policy_document.baseline_profile,
        candidate_profile=policy_document.candidate_b_profile,
    )
    document = feature_diagnostics_to_dict(diagnostics)
    document["feature_contract_sha256"] = sha256(settings.feature_contract_path)
    document["profiles_sha256"] = sha256(settings.profiles_path)
    output = write_json(document, settings.feature_diagnostics_path)
    manifest["sha256"]["feature_diagnostics"] = sha256(output)
    write_json(manifest, settings.freeze_manifest_path)
    return output


def bootstrap_models(settings: ModelTrainerSettings) -> Path:
    if settings.bootstrap_manifest_path.exists():
        raise RuntimeError("model bootstrap evidence already exists")
    verify_freeze_manifest(settings)
    development_path = settings.development_evidence_path
    development = benchmark_from_dict(
        json.loads(development_path.read_text(encoding="utf-8"))
    )
    if development.evaluation_role != "valid" or development.accessed_roles != (
        "train",
        "valid",
    ):
        raise ValueError("development evidence has an invalid role contract")
    decisions = evaluate_release(settings, development)
    assert_teaching_scenario(decisions)

    benchmark = build_benchmark(settings)
    _, profiles = load_profiles(settings.profiles_path)
    pipelines = FitModelBundles(benchmark).execute(
        tuple(profile.name for profile in profiles)
    )
    evaluations = {item.profile: item for item in development.profiles}
    feature_set = load_feature_contract(settings.feature_contract_path)
    provenance = _model_provenance(settings)
    tracker = MlflowModelTracker(
        settings.mlflow_tracking_uri, settings.mlflow_experiment_name
    )

    bundles: dict[str, dict[str, object]] = {}
    for profile in profiles:
        model_path, metadata_path = persist_model_bundle(
            pipeline=pipelines.get(profile.name),
            profile=profile,
            evaluation=evaluations[profile.name],
            feature_set=feature_set,
            feature_contract_sha256=sha256(settings.feature_contract_path),
            provenance=provenance,
            output_dir=settings.model_bundle_dir,
        )
        run_id = tracker.record(
            profile=profile,
            evaluation=evaluations[profile.name],
            pipeline=pipelines.get(profile.name),
            bundle_dir=model_path.parent,
            train_path=settings.split_dataset_dir / "train.csv",
            valid_path=settings.split_dataset_dir / "valid.csv",
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

    _publish_baseline(settings)
    document: dict[str, object] = {
        "schema_version": 1,
        "evaluation_role": "valid",
        "accessed_roles": ["train", "valid"],
        "bundles": bundles,
        "initial_deployed_profile": "baseline",
        "candidate_deployment_allowed": False,
        "candidate_deployment_reason": _candidate_deployment_reason(settings),
        "provenance": provenance,
    }
    write_json(_portable_bootstrap_document(document), settings.bootstrap_evidence_path)
    return write_json(document, settings.bootstrap_manifest_path)


def reconcile_bootstrap_evidence(settings: ModelTrainerSettings) -> Path:
    document = json.loads(settings.bootstrap_manifest_path.read_text(encoding="utf-8"))
    return write_json(
        _portable_bootstrap_document(document), settings.bootstrap_evidence_path
    )


def run_final(settings: ModelTrainerSettings, sealed_test_token: str) -> Path:
    _assert_canonical_test_not_finalized(settings)
    if not settings.bootstrap_manifest_path.exists():
        raise RuntimeError("bootstrap models before the sealed test evaluation")
    output = settings.artifact_dir / "final-benchmark.json"
    if output.exists():
        raise RuntimeError(
            "sealed test evidence already exists; final evaluation is one-shot"
        )
    verify_freeze_manifest(settings)
    benchmark = build_benchmark(settings)
    bootstrap = json.loads(settings.bootstrap_manifest_path.read_text(encoding="utf-8"))
    pipelines = FittedModels.from_mapping(
        {
            profile: load_model_bundle(
                Path(item["model_path"]), Path(item["metadata_path"])
            )
            for profile, item in bootstrap["bundles"].items()
        }
    )
    result = ConfirmFrozenModels(benchmark).execute(
        sealed_test_token=sealed_test_token, fitted_models=pipelines
    )
    output = write_json(benchmark_to_dict(result), output)
    _complete_final(settings, result, output, benchmark)
    return output


def reconcile_final(settings: ModelTrainerSettings) -> Path:
    output = settings.artifact_dir / "final-benchmark.json"
    if not output.exists():
        raise FileNotFoundError("final benchmark evidence does not exist")
    manifest = verify_freeze_manifest(settings)
    if manifest.get("sealed_test_status") == "evaluated_once":
        return output
    result = benchmark_from_dict(json.loads(output.read_text(encoding="utf-8")))
    if result.evaluation_role != "test" or result.accessed_roles != (
        "train",
        "valid",
        "test",
    ):
        raise ValueError("final benchmark evidence has an invalid role contract")
    _complete_final(settings, result, output, None)
    return output


def _complete_final(
    settings: ModelTrainerSettings,
    result: BenchmarkResult,
    output: Path,
    benchmark: SklearnBenchmark | None,
) -> None:
    decisions = evaluate_release(settings, result)
    write_json(
        {
            "schema_version": 1,
            "evaluation_role": "test",
            "decisions": decisions_to_dict(decisions),
        },
        settings.artifact_dir / "final-release-decisions.json",
    )
    _track_benchmark(settings, result, output)
    if not teaching_scenario_matches(decisions):
        write_json(
            {
                "schema_version": 1,
                "status": "SCENARIO_REVIEW_REQUIRED",
                "decisions": decisions_to_dict(decisions),
                "deployment_allowed": False,
                "post_test_policy_or_profile_tuning_allowed": False,
            },
            settings.artifact_dir / "scenario-review.json",
        )
        finalize_manifest(
            settings,
            output,
            decisions,
            (),
            release_status="scenario_review",
        )
        _write_canonical_evidence(
            settings=settings,
            result=result,
            decisions=decisions,
            deployment_allowed=False,
        )
        raise RuntimeError(
            "sealed test did not reproduce the target scenario; deployment is blocked"
        )
    bootstrap = json.loads(settings.bootstrap_manifest_path.read_text(encoding="utf-8"))
    bundles = tuple(Path(item["model_path"]) for item in bootstrap["bundles"].values())
    finalize_manifest(
        settings,
        output,
        decisions,
        bundles,
        release_status="release_approved",
    )
    _write_canonical_evidence(
        settings=settings,
        result=result,
        decisions=decisions,
        deployment_allowed=True,
    )


def _track_benchmark(
    settings: ModelTrainerSettings,
    result: BenchmarkResult,
    evidence_path: Path,
) -> tuple[str, ...]:
    tracked = {
        "feature_contract_sha256": sha256(settings.feature_contract_path),
        "profiles_sha256": sha256(settings.profiles_path),
        "evaluation_sha256": sha256(settings.evaluation_path),
        "release_policy_sha256": sha256(settings.release_policy_path),
        "dvc_lock_sha256": sha256(settings.dvc_lock_path),
    }
    for role in result.accessed_roles:
        tracked[f"{role}_dataset_sha256"] = sha256(
            settings.split_dataset_dir / f"{role}.csv"
        )
    return MlflowBenchmarkTracker(
        settings.mlflow_tracking_uri,
        settings.mlflow_experiment_name,
    ).record(result, evidence_path, tracked)


def _model_provenance(settings: ModelTrainerSettings) -> dict[str, str]:
    data_manifest = json.loads(settings.data_manifest_path.read_text(encoding="utf-8"))
    role_datasets = data_manifest["role_datasets"]
    split_seed = data_manifest.get("configuration", {}).get("split_seed")
    if split_seed is None:
        split_seed = load_split_config(settings.split_config_path).random_seed
    return {
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "git_worktree_dirty": str(
            bool(subprocess.check_output(["git", "status", "--porcelain"], text=True))
        ).lower(),
        "dvc_lock_revision": sha256(settings.dvc_lock_path),
        "raw_data_hash": data_manifest["source"]["archive_sha256"],
        "train_data_hash": role_datasets["train"]["sha256"],
        "valid_data_hash": role_datasets["valid"]["sha256"],
        "test_data_hash": role_datasets["test"]["sha256"],
        "split_seed": str(split_seed),
        "data_revision": str(data_manifest.get("revision", "v1")),
        "model_input_config_hash": sha256(settings.feature_contract_path),
        "model_profile_config_hash": sha256(settings.profiles_path),
        "evaluation_config_hash": sha256(settings.evaluation_path),
        "release_policy_config_hash": sha256(settings.release_policy_path),
    }


def _publish_baseline(settings: ModelTrainerSettings) -> None:
    source = settings.model_bundle_dir / "baseline"
    settings.deployed_model_dir.mkdir(parents=True, exist_ok=True)
    for name in ("model.joblib", "metadata.json"):
        shutil.copy2(source / name, settings.deployed_model_dir / name)
    write_json(
        {
            "schema_version": 1,
            "profile": "baseline",
            "model_sha256": sha256(settings.deployed_model_dir / "model.joblib"),
            "candidate_deployment_allowed": False,
        },
        settings.deployed_model_dir / "deployment.json",
    )


def _candidate_deployment_reason(settings: ModelTrainerSettings) -> str:
    if not settings.canonical_evidence_path.exists():
        return "awaiting_sealed_test"
    document = json.loads(settings.canonical_evidence_path.read_text(encoding="utf-8"))
    if document.get("deployment_allowed") is True:
        return "approved_but_not_published_by_bootstrap"
    return "sealed_test_scenario_review"


def _write_canonical_evidence(
    *,
    settings: ModelTrainerSettings,
    result: BenchmarkResult,
    decisions: tuple[ReleaseDecision, ...],
    deployment_allowed: bool,
) -> Path:
    final_path = settings.artifact_dir / "final-benchmark.json"
    document = {
        "schema_version": 1,
        "status": "APPROVED" if deployment_allowed else "SCENARIO_REVIEW_REQUIRED",
        "deployment_allowed": deployment_allowed,
        "sealed_test": {
            "status": "evaluated_once",
            "artifact_sha256": sha256(final_path),
            "dataset_sha256": sha256(settings.split_dataset_dir / "test.csv"),
            "accessed_roles": list(result.accessed_roles),
            "freeze_manifest_path": _workspace_relative(settings.freeze_manifest_path),
            "freeze_manifest_sha256": sha256(settings.freeze_manifest_path),
        },
        "profiles": benchmark_to_dict(result)["profiles"],
        "decisions": decisions_to_dict(decisions),
        "configuration": {
            "feature_contract_sha256": sha256(settings.feature_contract_path),
            "profiles_sha256": sha256(settings.profiles_path),
            "evaluation_sha256": sha256(settings.evaluation_path),
            "release_policy_sha256": sha256(settings.release_policy_path),
        },
        "post_test_tuning_allowed": False,
    }
    return write_json(document, settings.canonical_evidence_path)


def _workspace_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        raise ValueError(f"evidence path is outside the workspace: {path}") from None


def _portable_bootstrap_document(
    document: dict[str, object],
) -> dict[str, object]:
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


def _assert_canonical_test_not_finalized(settings: ModelTrainerSettings) -> None:
    path = settings.canonical_evidence_path
    if not path.exists():
        return
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("sealed_test", {}).get("status") == "evaluated_once":
        raise RuntimeError(
            "canonical sealed test was already evaluated; start a separately approved "
            "scenario revision instead of overwriting the evidence"
        )
