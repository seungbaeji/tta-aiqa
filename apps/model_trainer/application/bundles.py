"""Frozen bundle construction use cases for Model Trainer."""

from pathlib import Path

from aiqa_core.domain import FeatureSet
from aiqa_model.application import fit_model_bundles
from aiqa_model.domain import ModelProfileCatalog, ModelProfileSelection
from aiqa_model.ports import FrozenModelFitter
from aiqa_qa.domain import ReleasePolicy

from model_trainer.application.release import assert_teaching_scenario, evaluate_release
from model_trainer.domain import FrozenModelBundle, ModelTrainerConfiguration
from model_trainer.ports import (
    BaselineModelPublisher,
    BootstrapEvidenceStore,
    JsonDocumentStore,
    ModelBundleStore,
    ModelEvidenceCodec,
    ModelRunTracker,
    ReleaseProvenance,
    SourceRevisionControl,
)


def bootstrap_models(
    configuration: ModelTrainerConfiguration,
    *,
    profile_catalog: ModelProfileCatalog,
    feature_set: FeatureSet,
    fitter: FrozenModelFitter,
    release_policy: ReleasePolicy,
    documents: JsonDocumentStore,
    evidence_codec: ModelEvidenceCodec,
    bundle_store: ModelBundleStore,
    model_tracker: ModelRunTracker,
    bootstrap_evidence: BootstrapEvidenceStore,
    baseline_publisher: BaselineModelPublisher,
    source_control: SourceRevisionControl,
    provenance: ReleaseProvenance,
) -> Path:
    """Fit train/valid bundles and then write the immutable pre-test release freeze."""
    provenance.assert_not_frozen(configuration)
    if configuration.bootstrap_manifest_path.exists():
        raise RuntimeError("model bootstrap evidence already exists")
    source_commit = source_control.capture_clean()
    development = evidence_codec.benchmark_result(
        documents.read(configuration.development_evidence_path)
    )
    if development.evaluation_role != "valid" or development.accessed_roles != (
        "train",
        "valid",
    ):
        raise ValueError("development evidence has an invalid role contract")
    decisions = evaluate_release(release_policy, development)
    assert_teaching_scenario(decisions)

    profiles = profile_catalog.profiles
    pipelines = fit_model_bundles(
        selection=ModelProfileSelection.from_names(
            profile.name for profile in profiles
        ),
        fitter=fitter,
    )
    evaluations = {item.profile: item for item in development.profiles}
    lineage = provenance.model_provenance(configuration, source_commit)
    configuration_digests = provenance.configuration_digests(configuration)
    bundles: dict[str, dict[str, object]] = {}
    frozen_bundles: list[FrozenModelBundle] = []
    for profile in profiles:
        pipeline = pipelines.get(profile.name)
        model_path, metadata_path = bundle_store.persist(
            pipeline=pipeline,
            profile=profile,
            evaluation=evaluations[profile.name],
            feature_set=feature_set,
            feature_contract_sha256=configuration_digests[
                "feature_contract_sha256"
            ],
            provenance=lineage,
            output_dir=configuration.model_bundle_dir,
        )
        run_id = model_tracker.record(
            profile=profile,
            evaluation=evaluations[profile.name],
            pipeline=pipeline,
            bundle_dir=model_path.parent,
            train_path=configuration.split_dataset_dir / "train.csv",
            valid_path=configuration.split_dataset_dir / "valid.csv",
            provenance=lineage,
        )
        frozen = FrozenModelBundle(
            profile=profile.name,
            model_path=model_path,
            metadata_path=metadata_path,
            mlflow_run_id=run_id,
        )
        frozen_bundles.append(frozen)
        bundles[profile.name] = bootstrap_bundle_document(frozen, bundle_store)

    baseline_publisher.publish(configuration)
    document = {
        "schema_version": 1,
        "evaluation_role": "valid",
        "accessed_roles": ["train", "valid"],
        "bundles": bundles,
        "initial_deployed_profile": "baseline",
        "candidate_deployment_allowed": False,
        "candidate_deployment_reason": (
            bootstrap_evidence.candidate_deployment_reason(configuration)
        ),
        "provenance": lineage,
    }
    output = bootstrap_evidence.persist(document, configuration)
    provenance.write_freeze(
        configuration,
        source_commit=source_commit,
        bundles=tuple(frozen_bundles),
        decisions=decisions,
    )
    return output


def reconcile_bootstrap_evidence(
    configuration: ModelTrainerConfiguration,
    *,
    bootstrap_evidence: BootstrapEvidenceStore,
) -> Path:
    """Regenerate portable bootstrap evidence without changing the local artifact."""
    return bootstrap_evidence.reconcile(configuration)


def bootstrap_bundle_document(
    bundle: FrozenModelBundle,
    bundle_store: ModelBundleStore,
) -> dict[str, object]:
    """Create the reviewable bootstrap record for one persisted model bundle."""
    return {
        "model_path": str(bundle.model_path),
        "model_sha256": bundle_store.digest(bundle.model_path),
        "metadata_path": str(bundle.metadata_path),
        "metadata_sha256": bundle_store.digest(bundle.metadata_path),
        "mlflow_run_id": bundle.mlflow_run_id,
        "deployed": bundle.profile == "baseline",
    }
