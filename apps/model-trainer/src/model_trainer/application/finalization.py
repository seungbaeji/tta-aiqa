"""Sealed-test finalization use cases for Model Trainer."""

from pathlib import Path

from aiqa_model.application import confirm_frozen_models
from aiqa_model.domain import (
    BenchmarkResult,
    ModelProfileCatalog,
    ModelProfileSelection,
    SealedTestConfirmation,
)
from aiqa_model.ports import FittedModels, FrozenModelEvaluator
from aiqa_qa.domain import Decision, ReleaseDecision, ReleasePolicy

from model_trainer.application.development import track_benchmark
from model_trainer.application.release import (
    decisions_to_dict,
    evaluate_release,
    teaching_scenario_matches,
)
from model_trainer.domain import FrozenModelBundle, ModelTrainerConfiguration
from model_trainer.ports import (
    BenchmarkRunTracker,
    CanonicalEvidenceGuard,
    JsonDocumentStore,
    ModelBundleStore,
    ModelEvidenceCodec,
    ReleaseProvenance,
    SourceRevisionControl,
)


def run_final(
    configuration: ModelTrainerConfiguration,
    sealed_test_token: str,
    *,
    profile_catalog: ModelProfileCatalog,
    evaluator: FrozenModelEvaluator,
    release_policy: ReleasePolicy,
    documents: JsonDocumentStore,
    evidence_codec: ModelEvidenceCodec,
    bundle_store: ModelBundleStore,
    benchmark_tracker: BenchmarkRunTracker,
    source_control: SourceRevisionControl,
    canonical_guard: CanonicalEvidenceGuard,
    provenance: ReleaseProvenance,
) -> Path:
    """Evaluate verified frozen bundles against the sealed test role exactly once."""
    confirmation = SealedTestConfirmation(sealed_test_token)
    canonical_guard.assert_not_finalized(configuration)
    if not configuration.bootstrap_manifest_path.exists():
        raise RuntimeError("bootstrap models before the sealed test evaluation")
    output = configuration.artifact_dir / "final-benchmark.json"
    if output.exists():
        raise RuntimeError(
            "sealed test evidence already exists; final evaluation is one-shot"
        )
    release = provenance.verify_freeze(configuration)
    source_control.verify(release.source_commit)
    pipelines = FittedModels.from_mapping(
        {
            bundle.profile: bundle_store.load(bundle.model_path, bundle.metadata_path)
            for bundle in release.bundles
        }
    )
    result = confirm_frozen_models(
        confirmation=confirmation,
        selection=ModelProfileSelection.from_names(
            profile.name for profile in profile_catalog.profiles
        ),
        evaluator=evaluator,
        fitted_models=pipelines,
    )
    output = documents.write(evidence_codec.benchmark_document(result), output)
    complete_final(
        configuration,
        result,
        output,
        source_commit=release.source_commit,
        bundles=release.bundles,
        release_policy=release_policy,
        documents=documents,
        evidence_codec=evidence_codec,
        benchmark_tracker=benchmark_tracker,
        provenance=provenance,
    )
    return output


def reconcile_final(
    configuration: ModelTrainerConfiguration,
    *,
    release_policy: ReleasePolicy,
    documents: JsonDocumentStore,
    evidence_codec: ModelEvidenceCodec,
    benchmark_tracker: BenchmarkRunTracker,
    source_control: SourceRevisionControl,
    provenance: ReleaseProvenance,
) -> Path:
    """Complete missing final documents without reopening the sealed test CSV."""
    output = configuration.artifact_dir / "final-benchmark.json"
    if not output.exists():
        raise FileNotFoundError("final benchmark evidence does not exist")
    release = provenance.verify_freeze(configuration)
    source_control.verify(release.source_commit)
    if configuration.release_manifest_path.exists():
        return output
    result = evidence_codec.benchmark_result(documents.read(output))
    if result.evaluation_role != "test" or result.accessed_roles != (
        "train",
        "valid",
        "test",
    ):
        raise ValueError("final benchmark evidence has an invalid role contract")
    complete_final(
        configuration,
        result,
        output,
        source_commit=release.source_commit,
        bundles=release.bundles,
        release_policy=release_policy,
        documents=documents,
        evidence_codec=evidence_codec,
        benchmark_tracker=benchmark_tracker,
        provenance=provenance,
    )
    return output


def complete_final(
    configuration: ModelTrainerConfiguration,
    result: BenchmarkResult,
    output: Path,
    *,
    source_commit: str,
    bundles: tuple[FrozenModelBundle, ...],
    release_policy: ReleasePolicy,
    documents: JsonDocumentStore,
    evidence_codec: ModelEvidenceCodec,
    benchmark_tracker: BenchmarkRunTracker,
    provenance: ReleaseProvenance,
) -> None:
    """Write final QA, canonical evidence, and a separate release manifest."""
    decisions = evaluate_release(release_policy, result)
    documents.write(
        {
            "schema_version": 1,
            "evaluation_role": "test",
            "decisions": decisions_to_dict(decisions),
        },
        configuration.artifact_dir / "final-release-decisions.json",
    )
    final_mlflow_run_ids = track_benchmark(
        configuration,
        result,
        output,
        source_commit=source_commit,
        tracker=benchmark_tracker,
        provenance=provenance,
    )
    deployment_allowed = teaching_scenario_matches(decisions)
    approved_profile = approved_profile_for(decisions) if deployment_allowed else None
    if not deployment_allowed:
        documents.write(
            {
                "schema_version": 1,
                "status": "SCENARIO_REVIEW_REQUIRED",
                "decisions": decisions_to_dict(decisions),
                "deployment_allowed": False,
                "post_test_policy_or_profile_tuning_allowed": False,
            },
            configuration.artifact_dir / "scenario-review.json",
        )
    profiles = evidence_codec.benchmark_document(result)["profiles"]
    provenance.write_canonical_evidence(
        configuration,
        final_evidence_path=output,
        accessed_roles=result.accessed_roles,
        profiles=profiles,
        decisions=decisions,
        deployment_allowed=deployment_allowed,
    )
    provenance.write_release_manifest(
        configuration,
        final_evidence_path=output,
        canonical_evidence_path=configuration.canonical_evidence_path,
        bundles=bundles,
        decisions=decisions,
        final_mlflow_run_ids=final_mlflow_run_ids,
        approved_profile=approved_profile,
    )
    if not deployment_allowed:
        raise RuntimeError(
            "sealed test did not reproduce the target scenario; deployment is blocked"
        )


def approved_profile_for(decisions: tuple[ReleaseDecision, ...]) -> str:
    """Return the one approved candidate required by the teaching scenario."""
    approved = tuple(
        decision.profile
        for decision in decisions
        if decision.decision is Decision.APPROVE
    )
    if len(approved) != 1:
        raise RuntimeError("teaching scenario requires exactly one approved candidate")
    return approved[0]
