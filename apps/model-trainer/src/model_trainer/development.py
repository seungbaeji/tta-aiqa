"""Development and diagnostics workflows for the Model Trainer."""

import json
from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_model.adapters import (
    MlflowBenchmarkTracker,
    SklearnBenchmark,
    benchmark_to_dict,
    feature_diagnostics_to_dict,
    load_evaluation_plan,
    load_profiles,
)
from aiqa_model.application import develop_models, diagnose_features
from aiqa_model.domain import BenchmarkResult
from aiqa_qa.adapters import load_release_policy

from model_trainer.provenance import (
    sha256,
    verify_freeze_manifest,
    write_freeze_manifest,
    write_json,
)
from model_trainer.release import (
    assert_teaching_scenario,
    decisions_to_dict,
    evaluate_release,
)
from model_trainer.workflow import ModelTrainerConfiguration


def build_benchmark(configuration: ModelTrainerConfiguration) -> SklearnBenchmark:
    """Build the concrete sklearn benchmark from versioned configuration files."""
    feature_set = load_feature_contract(configuration.feature_contract_path)
    random_seed, profiles = load_profiles(configuration.profiles_path)
    evaluation = load_evaluation_plan(configuration.evaluation_path)
    return SklearnBenchmark(
        configuration.split_dataset_dir,
        feature_set,
        profiles,
        evaluation,
        random_seed,
    )


def run_development(configuration: ModelTrainerConfiguration) -> Path:
    """Create train/valid evidence and freeze inputs before sealed evaluation."""
    assert_canonical_test_not_finalized(configuration)
    result = develop_models(benchmark=build_benchmark(configuration))
    output = write_json(
        benchmark_to_dict(result),
        configuration.artifact_dir / "development-benchmark.json",
    )
    write_json(benchmark_to_dict(result), configuration.development_evidence_path)
    decisions = evaluate_release(configuration, result)
    assert_teaching_scenario(decisions)
    write_json(
        {
            "schema_version": 1,
            "evaluation_role": "valid",
            "decisions": decisions_to_dict(decisions),
        },
        configuration.artifact_dir / "development-release-decisions.json",
    )
    track_benchmark(configuration, result, output)
    write_freeze_manifest(
        configuration, configuration.development_evidence_path, decisions
    )
    return output


def run_feature_diagnostics(configuration: ModelTrainerConfiguration) -> Path:
    """Produce development-only feature diagnostics for the teaching record."""
    manifest = verify_freeze_manifest(configuration)
    policy_document, _ = load_release_policy(configuration.release_policy_path)
    diagnostics = diagnose_features(
        benchmark=build_benchmark(configuration),
        baseline_profile=policy_document.baseline_profile,
        candidate_profile=policy_document.candidate_b_profile,
    )
    document = feature_diagnostics_to_dict(diagnostics)
    document["feature_contract_sha256"] = sha256(
        configuration.feature_contract_path
    )
    document["profiles_sha256"] = sha256(configuration.profiles_path)
    output = write_json(document, configuration.feature_diagnostics_path)
    manifest["sha256"]["feature_diagnostics"] = sha256(output)
    write_json(manifest, configuration.freeze_manifest_path)
    return output


def track_benchmark(
    configuration: ModelTrainerConfiguration,
    result: BenchmarkResult,
    evidence_path: Path,
) -> tuple[str, ...]:
    """Record benchmark evidence and immutable input hashes in MLflow."""
    tracked = {
        "feature_contract_sha256": sha256(configuration.feature_contract_path),
        "profiles_sha256": sha256(configuration.profiles_path),
        "evaluation_sha256": sha256(configuration.evaluation_path),
        "release_policy_sha256": sha256(configuration.release_policy_path),
        "dvc_lock_sha256": sha256(configuration.dvc_lock_path),
    }
    for role in result.accessed_roles:
        tracked[f"{role}_dataset_sha256"] = sha256(
            configuration.split_dataset_dir / f"{role}.csv"
        )
    return MlflowBenchmarkTracker(
        configuration.mlflow_tracking_uri,
        configuration.mlflow_experiment_name,
    ).record(result, evidence_path, tracked)


def assert_canonical_test_not_finalized(
    configuration: ModelTrainerConfiguration,
) -> None:
    """Reject mutation of a scenario whose canonical sealed test is final."""
    path = configuration.canonical_evidence_path
    if not path.exists():
        return
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("sealed_test", {}).get("status") == "evaluated_once":
        raise RuntimeError(
            "canonical sealed test was already evaluated; start a separately approved "
            "scenario revision instead of overwriting the evidence"
        )
