"""Development and feature-diagnostics use cases for Model Trainer."""

from pathlib import Path

from aiqa_model.application import develop_models, diagnose_features
from aiqa_model.domain import (
    BenchmarkResult,
    FeatureDiagnosticsRequest,
    ModelProfileCatalog,
    ModelProfileSelection,
)
from aiqa_model.ports import DevelopmentModelEvaluator, FeatureDiagnostician
from aiqa_qa.domain import ReleasePolicy

from model_trainer.application.release import (
    assert_teaching_scenario,
    decisions_to_dict,
    evaluate_release,
)
from model_trainer.domain import ModelTrainerConfiguration
from model_trainer.ports import (
    BenchmarkRunTracker,
    CanonicalEvidenceGuard,
    JsonDocumentStore,
    ModelEvidenceCodec,
    ReleaseProvenance,
    SourceRevisionControl,
)


def run_development(
    configuration: ModelTrainerConfiguration,
    *,
    profile_catalog: ModelProfileCatalog,
    evaluator: DevelopmentModelEvaluator,
    release_policy: ReleasePolicy,
    documents: JsonDocumentStore,
    evidence_codec: ModelEvidenceCodec,
    tracker: BenchmarkRunTracker,
    source_control: SourceRevisionControl,
    canonical_guard: CanonicalEvidenceGuard,
    provenance: ReleaseProvenance,
) -> Path:
    """Evaluate every configured model using train/valid data before release freeze."""
    canonical_guard.assert_not_finalized(configuration)
    provenance.assert_not_frozen(configuration)
    source_commit = source_control.capture()
    result = develop_models(
        selection=ModelProfileSelection.from_names(
            profile.name for profile in profile_catalog.profiles
        ),
        evaluator=evaluator,
    )
    evidence = evidence_codec.benchmark_document(result)
    output = documents.write(
        evidence,
        configuration.artifact_dir / "development-benchmark.json",
    )
    documents.write(evidence, configuration.development_evidence_path)
    decisions = evaluate_release(release_policy, result)
    assert_teaching_scenario(decisions)
    documents.write(
        {
            "schema_version": 1,
            "evaluation_role": "valid",
            "decisions": decisions_to_dict(decisions),
        },
        configuration.artifact_dir / "development-release-decisions.json",
    )
    track_benchmark(
        configuration,
        result,
        output,
        source_commit=source_commit,
        tracker=tracker,
        provenance=provenance,
    )
    return output


def run_feature_diagnostics(
    configuration: ModelTrainerConfiguration,
    *,
    release_policy: ReleasePolicy,
    diagnostician: FeatureDiagnostician,
    documents: JsonDocumentStore,
    evidence_codec: ModelEvidenceCodec,
    provenance: ReleaseProvenance,
) -> Path:
    """Produce train/valid-only feature diagnostics before the release is frozen."""
    provenance.assert_not_frozen(configuration)
    diagnostics = diagnose_features(
        request=FeatureDiagnosticsRequest(
            baseline_profile=release_policy.baseline_profile,
            candidate_profile=release_policy.candidate_b_profile,
        ),
        diagnostician=diagnostician,
    )
    document = evidence_codec.diagnostics_document(diagnostics)
    document["feature_contract_sha256"] = provenance.configuration_digests(
        configuration
    )["feature_contract_sha256"]
    document["profiles_sha256"] = provenance.configuration_digests(configuration)[
        "profiles_sha256"
    ]
    return documents.write(document, configuration.feature_diagnostics_path)


def track_benchmark(
    configuration: ModelTrainerConfiguration,
    result: BenchmarkResult,
    evidence_path: Path,
    *,
    source_commit: str,
    tracker: BenchmarkRunTracker,
    provenance: ReleaseProvenance,
) -> dict[str, str]:
    """Record evidence only for dataset roles consumed by this benchmark stage."""
    runs = tracker.record(
        result,
        evidence_path,
        provenance.tracking_provenance(
            configuration,
            source_commit,
            roles=result.accessed_roles,
        ),
    )
    return {
        evaluation.profile: run_id
        for evaluation, run_id in zip(result.profiles, runs, strict=True)
    }
