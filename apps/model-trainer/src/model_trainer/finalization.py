"""Sealed-test finalization and canonical evidence workflows."""

import json
from pathlib import Path

from aiqa_model.adapters import (
    benchmark_from_dict,
    benchmark_to_dict,
    load_model_bundle,
)
from aiqa_model.application import confirm_frozen_models
from aiqa_model.domain import BenchmarkResult
from aiqa_model.ports import FittedModels
from aiqa_qa.domain import ReleaseDecision

from model_trainer.development import (
    assert_canonical_test_not_finalized,
    build_benchmark,
    track_benchmark,
)
from model_trainer.provenance import (
    finalize_manifest,
    sha256,
    verify_freeze_manifest,
    write_json,
)
from model_trainer.release import (
    decisions_to_dict,
    evaluate_release,
    teaching_scenario_matches,
)
from model_trainer.workflow import ModelTrainerConfiguration


def run_final(
    configuration: ModelTrainerConfiguration, sealed_test_token: str
) -> Path:
    """Evaluate frozen bundles against the sealed test role exactly once."""
    assert_canonical_test_not_finalized(configuration)
    if not configuration.bootstrap_manifest_path.exists():
        raise RuntimeError("bootstrap models before the sealed test evaluation")
    output = configuration.artifact_dir / "final-benchmark.json"
    if output.exists():
        raise RuntimeError(
            "sealed test evidence already exists; final evaluation is one-shot"
        )
    verify_freeze_manifest(configuration)
    benchmark = build_benchmark(configuration)
    bootstrap = json.loads(
        configuration.bootstrap_manifest_path.read_text(encoding="utf-8")
    )
    pipelines = FittedModels.from_mapping(
        {
            profile: load_model_bundle(
                Path(item["model_path"]), Path(item["metadata_path"])
            )
            for profile, item in bootstrap["bundles"].items()
        }
    )
    result = confirm_frozen_models(
        benchmark=benchmark,
        sealed_test_token=sealed_test_token,
        fitted_models=pipelines,
    )
    output = write_json(benchmark_to_dict(result), output)
    complete_final(configuration, result, output)
    return output


def reconcile_final(configuration: ModelTrainerConfiguration) -> Path:
    """Complete missing final evidence bookkeeping without re-running the test."""
    output = configuration.artifact_dir / "final-benchmark.json"
    if not output.exists():
        raise FileNotFoundError("final benchmark evidence does not exist")
    manifest = verify_freeze_manifest(configuration)
    if manifest.get("sealed_test_status") == "evaluated_once":
        return output
    result = benchmark_from_dict(json.loads(output.read_text(encoding="utf-8")))
    if result.evaluation_role != "test" or result.accessed_roles != (
        "train",
        "valid",
        "test",
    ):
        raise ValueError("final benchmark evidence has an invalid role contract")
    complete_final(configuration, result, output)
    return output


def complete_final(
    configuration: ModelTrainerConfiguration,
    result: BenchmarkResult,
    output: Path,
) -> None:
    """Record final decisions and either release or block the teaching scenario."""
    decisions = evaluate_release(configuration, result)
    write_json(
        {
            "schema_version": 1,
            "evaluation_role": "test",
            "decisions": decisions_to_dict(decisions),
        },
        configuration.artifact_dir / "final-release-decisions.json",
    )
    track_benchmark(configuration, result, output)
    if not teaching_scenario_matches(decisions):
        write_json(
            {
                "schema_version": 1,
                "status": "SCENARIO_REVIEW_REQUIRED",
                "decisions": decisions_to_dict(decisions),
                "deployment_allowed": False,
                "post_test_policy_or_profile_tuning_allowed": False,
            },
            configuration.artifact_dir / "scenario-review.json",
        )
        finalize_manifest(
            configuration,
            output,
            decisions,
            (),
            release_status="scenario_review",
        )
        write_canonical_evidence(
            configuration=configuration,
            result=result,
            decisions=decisions,
            deployment_allowed=False,
        )
        raise RuntimeError(
            "sealed test did not reproduce the target scenario; deployment is blocked"
        )
    bootstrap = json.loads(
        configuration.bootstrap_manifest_path.read_text(encoding="utf-8")
    )
    bundles = tuple(Path(item["model_path"]) for item in bootstrap["bundles"].values())
    finalize_manifest(
        configuration,
        output,
        decisions,
        bundles,
        release_status="release_approved",
    )
    write_canonical_evidence(
        configuration=configuration,
        result=result,
        decisions=decisions,
        deployment_allowed=True,
    )


def write_canonical_evidence(
    *,
    configuration: ModelTrainerConfiguration,
    result: BenchmarkResult,
    decisions: tuple[ReleaseDecision, ...],
    deployment_allowed: bool,
) -> Path:
    """Persist the immutable canonical evidence after sealed-test finalization."""
    final_path = configuration.artifact_dir / "final-benchmark.json"
    document = {
        "schema_version": 1,
        "status": "APPROVED" if deployment_allowed else "SCENARIO_REVIEW_REQUIRED",
        "deployment_allowed": deployment_allowed,
        "sealed_test": {
            "status": "evaluated_once",
            "artifact_sha256": sha256(final_path),
            "dataset_sha256": sha256(configuration.split_dataset_dir / "test.csv"),
            "accessed_roles": list(result.accessed_roles),
            "freeze_manifest_path": workspace_relative(
                configuration.freeze_manifest_path
            ),
            "freeze_manifest_sha256": sha256(configuration.freeze_manifest_path),
        },
        "profiles": benchmark_to_dict(result)["profiles"],
        "decisions": decisions_to_dict(decisions),
        "configuration": {
            "feature_contract_sha256": sha256(configuration.feature_contract_path),
            "profiles_sha256": sha256(configuration.profiles_path),
            "evaluation_sha256": sha256(configuration.evaluation_path),
            "release_policy_sha256": sha256(configuration.release_policy_path),
        },
        "post_test_tuning_allowed": False,
    }
    return write_json(document, configuration.canonical_evidence_path)


def workspace_relative(path: Path) -> str:
    """Return a portable workspace-relative evidence path."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        raise ValueError(f"evidence path is outside the workspace: {path}") from None
