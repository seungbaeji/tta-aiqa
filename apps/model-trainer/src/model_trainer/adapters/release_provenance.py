"""Release-freeze and release-manifest orchestration for Model Trainer."""

from __future__ import annotations

from pathlib import Path

from aiqa_qa.domain import Decision, ReleaseDecision

from model_trainer.adapters.documents import (
    ApprovedModelDocument,
    ArtifactDigestDocument,
    CanonicalReleaseEvidenceDocument,
    CanonicalReleaseSealedTestDocument,
    DataLineageDocument,
    FrozenDataDocument,
    ModelBundleDocument,
    ReleaseDecisionDocument,
    ReleaseFreezeDocument,
    ReleaseManifestDocument,
    SourceRevisionDocument,
)
from model_trainer.adapters.json_files import (
    read_json_mapping,
    relative_path,
    resolve_relative_path,
    sha256_file,
    write_json_mapping,
)
from model_trainer.adapters.source_control import GitRevision
from model_trainer.domain import (
    FrozenModelBundle,
    FrozenRelease,
    ModelTrainerConfiguration,
)

FROZEN_CONFIGURATION_PATHS = {
    "feature_contract_sha256": "feature_contract_path",
    "feature_sets_sha256": "feature_sets_path",
    "profiles_sha256": "profiles_path",
    "evaluation_sha256": "evaluation_path",
    "release_policy_sha256": "release_policy_path",
}
MODEL_DATASET_ROLES = ("train", "valid")
RELEASE_DATASET_ROLES = (*MODEL_DATASET_ROLES, "test")


def artifact_digest(path: Path, repository_root: Path) -> ArtifactDigestDocument:
    """Create a portable content-addressed reference for one generated artifact."""
    return ArtifactDigestDocument(
        path=relative_path(path, repository_root),
        sha256=sha256_file(path),
    )


def configuration_digests(
    configuration: ModelTrainerConfiguration,
) -> dict[str, str]:
    """Calculate all versioned model and release configuration digests once."""
    return {
        name: sha256_file(Path(getattr(configuration, path_name)))
        for name, path_name in FROZEN_CONFIGURATION_PATHS.items()
    }


def load_data_lineage(configuration: ModelTrainerConfiguration) -> DataLineageDocument:
    """Load the Pydantic-validated DVC/data-lineage evidence for this revision."""
    return DataLineageDocument.model_validate(
        read_json_mapping(configuration.data_manifest_path)
    )


def role_dataset_reference(
    configuration: ModelTrainerConfiguration,
    lineage: DataLineageDocument,
    role: str,
) -> ArtifactDigestDocument:
    """Verify one role CSV against lineage evidence and return its actual digest."""
    try:
        expected = lineage.role_datasets[role]
    except KeyError:
        raise ValueError(
            f"data-lineage evidence does not define the {role} role"
        ) from None
    path = configuration.split_dataset_dir / f"{role}.csv"
    actual = sha256_file(path)
    if actual != expected.sha256:
        raise RuntimeError(
            f"{role} dataset digest does not match data-lineage evidence"
        )
    return ArtifactDigestDocument(
        path=relative_path(path, configuration.repository_root),
        sha256=actual,
    )


def frozen_data_reference(
    configuration: ModelTrainerConfiguration,
) -> FrozenDataDocument:
    """Build the complete DVC/data identity that must exist before sealed test use."""
    lineage = load_data_lineage(configuration)
    dvc_lock_sha256 = sha256_file(configuration.dvc_lock_path)
    expected_lock = lineage.configuration.get("dvc_lock_sha256")
    if expected_lock is not None and expected_lock != dvc_lock_sha256:
        raise RuntimeError("dvc.lock digest does not match data-lineage evidence")
    return FrozenDataDocument(
        revision=lineage.revision,
        lineage_evidence_sha256=sha256_file(configuration.data_manifest_path),
        dvc_lock_sha256=dvc_lock_sha256,
        source_archive_sha256=lineage.source.archive_sha256,
        role_datasets={
            role: role_dataset_reference(configuration, lineage, role)
            for role in RELEASE_DATASET_ROLES
        },
    )


def tracking_provenance(
    configuration: ModelTrainerConfiguration,
    source_revision: GitRevision,
    *,
    roles: tuple[str, ...],
) -> dict[str, str]:
    """Create MLflow tags without hashing a dataset role the stage did not access."""
    lineage = load_data_lineage(configuration)
    provenance = {
        "git_commit": source_revision.commit,
        "dvc_lock_sha256": sha256_file(configuration.dvc_lock_path),
        "data_lineage_sha256": sha256_file(configuration.data_manifest_path),
        "data_revision": lineage.revision,
        "raw_data_hash": lineage.source.archive_sha256,
        **configuration_digests(configuration),
    }
    for role in roles:
        provenance[f"{role}_data_hash"] = role_dataset_reference(
            configuration, lineage, role
        ).sha256
    return provenance


def model_provenance(
    configuration: ModelTrainerConfiguration,
    source_revision: GitRevision,
) -> dict[str, str]:
    """Create train/valid-only model bundle provenance for MLflow and metadata."""
    return tracking_provenance(
        configuration,
        source_revision,
        roles=MODEL_DATASET_ROLES,
    )


def model_bundle_document(
    bundle: FrozenModelBundle,
    configuration: ModelTrainerConfiguration,
) -> ModelBundleDocument:
    """Convert one local bundle path into a portable frozen artifact reference."""
    return ModelBundleDocument(
        profile=bundle.profile,
        model_path=relative_path(bundle.model_path, configuration.model_bundle_dir),
        model_sha256=sha256_file(bundle.model_path),
        metadata_path=relative_path(
            bundle.metadata_path, configuration.model_bundle_dir
        ),
        metadata_sha256=sha256_file(bundle.metadata_path),
        mlflow_run_id=bundle.mlflow_run_id,
    )


def write_release_freeze(
    configuration: ModelTrainerConfiguration,
    *,
    source_revision: GitRevision,
    bundles: tuple[FrozenModelBundle, ...],
    decisions: tuple[ReleaseDecision, ...],
) -> Path:
    """Persist the immutable pre-test release freeze after bundle construction."""
    if configuration.freeze_manifest_path.exists():
        raise RuntimeError("release freeze already exists for this model revision")
    if not bundles:
        raise ValueError("release freeze requires at least one serialized model bundle")
    diagnostics = (
        artifact_digest(
            configuration.feature_diagnostics_path,
            configuration.repository_root,
        )
        if configuration.feature_diagnostics_path.exists()
        else None
    )
    document = ReleaseFreezeDocument(
        schema_version=3,
        source=SourceRevisionDocument(git_commit=source_revision.commit),
        data=frozen_data_reference(configuration),
        configuration=configuration_digests(configuration),
        development_evidence=artifact_digest(
            configuration.development_evidence_path,
            configuration.repository_root,
        ),
        feature_diagnostics=diagnostics,
        development_decisions=tuple(
            ReleaseDecisionDocument.from_domain(decision) for decision in decisions
        ),
        model_bundles=tuple(
            model_bundle_document(bundle, configuration) for bundle in bundles
        ),
        sealed_test=artifact_digest(
            configuration.split_dataset_dir / "test.csv",
            configuration.repository_root,
        ),
    )
    return write_json_mapping(
        document.model_dump(mode="json"), configuration.freeze_manifest_path
    )


def verify_release_freeze(
    configuration: ModelTrainerConfiguration,
) -> ReleaseFreezeDocument:
    """Verify every pre-test reference before the test CSV or bundle is opened."""
    document = ReleaseFreezeDocument.model_validate(
        read_json_mapping(configuration.freeze_manifest_path)
    )
    current_data = frozen_data_reference(configuration)
    current_configuration = configuration_digests(configuration)
    current_development = artifact_digest(
        configuration.development_evidence_path,
        configuration.repository_root,
    )
    current_diagnostics = (
        artifact_digest(
            configuration.feature_diagnostics_path,
            configuration.repository_root,
        )
        if configuration.feature_diagnostics_path.exists()
        else None
    )
    if (
        document.data != current_data
        or document.configuration != current_configuration
        or document.development_evidence != current_development
        or document.feature_diagnostics != current_diagnostics
    ):
        raise RuntimeError("frozen model inputs changed before sealed test evaluation")
    for bundle in document.model_bundles:
        model_path = resolve_relative_path(
            bundle.model_path, configuration.model_bundle_dir
        )
        metadata_path = resolve_relative_path(
            bundle.metadata_path, configuration.model_bundle_dir
        )
        if (
            sha256_file(model_path) != bundle.model_sha256
            or sha256_file(metadata_path) != bundle.metadata_sha256
        ):
            raise RuntimeError(
                "frozen model bundle changed before sealed test evaluation"
            )
    return document


def frozen_bundles_from_document(
    document: ReleaseFreezeDocument,
    configuration: ModelTrainerConfiguration,
) -> tuple[FrozenModelBundle, ...]:
    """Resolve verified frozen bundle records into local paths for final evaluation."""
    return tuple(
        FrozenModelBundle(
            profile=bundle.profile,
            model_path=resolve_relative_path(
                bundle.model_path, configuration.model_bundle_dir
            ),
            metadata_path=resolve_relative_path(
                bundle.metadata_path, configuration.model_bundle_dir
            ),
            mlflow_run_id=bundle.mlflow_run_id,
        )
        for bundle in document.model_bundles
    )


def write_release_manifest(
    configuration: ModelTrainerConfiguration,
    *,
    final_evidence_path: Path,
    canonical_evidence_path: Path,
    bundles: tuple[FrozenModelBundle, ...],
    decisions: tuple[ReleaseDecision, ...],
    final_mlflow_run_ids: dict[str, str],
    approved_profile: str | None,
) -> Path:
    """Record the post-test decision without mutating the pre-test freeze document."""
    if configuration.release_manifest_path.exists():
        raise RuntimeError("release manifest already exists for this model revision")
    freeze = verify_release_freeze(configuration)
    frozen_bundles = {bundle.profile: bundle for bundle in freeze.model_bundles}
    provided_bundles = {
        bundle.profile: model_bundle_document(bundle, configuration)
        for bundle in bundles
    }
    if provided_bundles != frozen_bundles:
        raise RuntimeError("release manifest bundles do not match the pre-test freeze")
    decisions_by_profile = {decision.profile: decision for decision in decisions}
    if approved_profile is not None:
        approved_decision = decisions_by_profile.get(approved_profile)
        if (
            approved_decision is None
            or approved_decision.decision is not Decision.APPROVE
        ):
            raise ValueError("approved profile must have an APPROVE release decision")
        if approved_profile not in final_mlflow_run_ids:
            raise ValueError("approved profile requires a final MLflow run ID")
    approved = (
        approved_model_document(
            frozen_bundles[approved_profile],
            feature_contract_sha256=freeze.configuration["feature_contract_sha256"],
            final_mlflow_run_id=final_mlflow_run_ids[approved_profile],
        )
        if approved_profile is not None
        else None
    )
    document = ReleaseManifestDocument(
        schema_version=1,
        release_status=(
            "release_approved" if approved_profile is not None else "scenario_review"
        ),
        deployment_allowed=approved_profile is not None,
        approved_profile=approved_profile,
        freeze_manifest=artifact_digest(
            configuration.freeze_manifest_path,
            configuration.repository_root,
        ),
        canonical_evidence=artifact_digest(
            canonical_evidence_path,
            configuration.repository_root,
        ),
        final_evidence=artifact_digest(
            final_evidence_path,
            configuration.repository_root,
        ),
        decisions=tuple(
            ReleaseDecisionDocument.from_domain(decision) for decision in decisions
        ),
        model_bundles={
            f"{bundle.profile}/{name}": digest
            for bundle in freeze.model_bundles
            for name, digest in (
                ("model.joblib", bundle.model_sha256),
                ("metadata.json", bundle.metadata_sha256),
            )
        },
        approved_model=approved,
    )
    return write_json_mapping(
        document.model_dump(mode="json"), configuration.release_manifest_path
    )


def approved_model_document(
    bundle: ModelBundleDocument,
    *,
    feature_contract_sha256: str,
    final_mlflow_run_id: str,
) -> ApprovedModelDocument:
    """Create the approved-model portion of a post-test release record."""
    return ApprovedModelDocument(
        profile=bundle.profile,
        model_sha256=bundle.model_sha256,
        metadata_sha256=bundle.metadata_sha256,
        feature_contract_sha256=feature_contract_sha256,
        model_mlflow_run_id=bundle.mlflow_run_id,
        final_mlflow_run_id=final_mlflow_run_id,
    )


def assert_release_not_frozen(configuration: ModelTrainerConfiguration) -> None:
    """Prevent development, diagnostics, or bootstrap from changing frozen inputs."""
    if configuration.freeze_manifest_path.exists():
        raise RuntimeError("release inputs are frozen; start a new model revision")


def write_canonical_evidence(
    configuration: ModelTrainerConfiguration,
    *,
    final_evidence_path: Path,
    accessed_roles: tuple[str, ...],
    profiles: object,
    decisions: tuple[ReleaseDecision, ...],
    deployment_allowed: bool,
) -> Path:
    """Persist canonical sealed-test evidence before the post-test manifest."""
    document = CanonicalReleaseEvidenceDocument(
        schema_version=1,
        status=("APPROVED" if deployment_allowed else "SCENARIO_REVIEW_REQUIRED"),
        deployment_allowed=deployment_allowed,
        sealed_test=CanonicalReleaseSealedTestDocument(
            status="evaluated_once",
            artifact_sha256=sha256_file(final_evidence_path),
            dataset_sha256=sha256_file(configuration.split_dataset_dir / "test.csv"),
            accessed_roles=accessed_roles,
            freeze_manifest_path=relative_path(
                configuration.freeze_manifest_path,
                configuration.repository_root,
            ),
            freeze_manifest_sha256=sha256_file(configuration.freeze_manifest_path),
        ),
        profiles=profiles,
        decisions=tuple(
            ReleaseDecisionDocument.from_domain(decision) for decision in decisions
        ),
        configuration=configuration_digests(configuration),
        post_test_tuning_allowed=False,
    )
    return write_json_mapping(
        document.model_dump(mode="json"), configuration.canonical_evidence_path
    )


class FilesystemReleaseProvenance:
    """Filesystem release evidence adapter with DVC, Git, and artifact verification."""

    def assert_not_frozen(self, configuration: ModelTrainerConfiguration) -> None:
        """Reject lifecycle work that would alter an already frozen release revision."""
        assert_release_not_frozen(configuration)

    def model_provenance(
        self, configuration: ModelTrainerConfiguration, source_commit: str
    ) -> dict[str, str]:
        """Return train/valid bundle lineage from the resolved source commit."""
        return model_provenance(configuration, GitRevision(source_commit))

    def tracking_provenance(
        self,
        configuration: ModelTrainerConfiguration,
        source_commit: str,
        *,
        roles: tuple[str, ...],
    ) -> dict[str, str]:
        """Return MLflow lineage only for roles consumed by this benchmark stage."""
        return tracking_provenance(
            configuration,
            GitRevision(source_commit),
            roles=roles,
        )

    def write_freeze(
        self,
        configuration: ModelTrainerConfiguration,
        *,
        source_commit: str,
        bundles: tuple[FrozenModelBundle, ...],
        decisions: tuple[ReleaseDecision, ...],
    ) -> Path:
        """Write an immutable pre-test freeze from finalized bundle artifacts."""
        return write_release_freeze(
            configuration,
            source_revision=GitRevision(source_commit),
            bundles=bundles,
            decisions=decisions,
        )

    def verify_freeze(self, configuration: ModelTrainerConfiguration) -> FrozenRelease:
        """Verify a persisted release freeze and expose only app-domain values."""
        document = verify_release_freeze(configuration)
        return FrozenRelease(
            source_commit=document.source.git_commit,
            bundles=frozen_bundles_from_document(document, configuration),
        )

    def write_release_manifest(
        self,
        configuration: ModelTrainerConfiguration,
        *,
        final_evidence_path: Path,
        canonical_evidence_path: Path,
        bundles: tuple[FrozenModelBundle, ...],
        decisions: tuple[ReleaseDecision, ...],
        final_mlflow_run_ids: dict[str, str],
        approved_profile: str | None,
    ) -> Path:
        """Persist the post-test release record for a verified frozen revision."""
        return write_release_manifest(
            configuration,
            final_evidence_path=final_evidence_path,
            canonical_evidence_path=canonical_evidence_path,
            bundles=bundles,
            decisions=decisions,
            final_mlflow_run_ids=final_mlflow_run_ids,
            approved_profile=approved_profile,
        )

    def write_canonical_evidence(
        self,
        configuration: ModelTrainerConfiguration,
        *,
        final_evidence_path: Path,
        accessed_roles: tuple[str, ...],
        profiles: object,
        decisions: tuple[ReleaseDecision, ...],
        deployment_allowed: bool,
    ) -> Path:
        """Persist canonical evidence before recording the release manifest."""
        return write_canonical_evidence(
            configuration,
            final_evidence_path=final_evidence_path,
            accessed_roles=accessed_roles,
            profiles=profiles,
            decisions=decisions,
            deployment_allowed=deployment_allowed,
        )

    def configuration_digests(
        self, configuration: ModelTrainerConfiguration
    ) -> dict[str, str]:
        """Return versioned configuration identities used by the release workflow."""
        return configuration_digests(configuration)
