"""Pydantic DTOs for Model Trainer lineage and release evidence."""

from __future__ import annotations

from typing import Literal

from aiqa_qa.domain import ReleaseDecision
from pydantic import BaseModel, ConfigDict, Field


class ArtifactDigestDocument(BaseModel):
    """One portable artifact path and its content digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str


class DataLineageSourceDocument(BaseModel):
    """Source checksum fields needed by model provenance."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    archive_sha256: str


class DataLineageRoleDocument(BaseModel):
    """One role dataset identity read from data-lineage evidence."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    path: str
    sha256: str


class DataLineageDocument(BaseModel):
    """Validated subset of DVC/data-lineage evidence used by model workflows."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    schema_version: int = Field(ge=1)
    revision: str = "v1"
    source: DataLineageSourceDocument
    configuration: dict[str, str] = Field(default_factory=dict)
    role_datasets: dict[str, DataLineageRoleDocument]


class SourceRevisionDocument(BaseModel):
    """Source identity recorded in an immutable pre-test freeze."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    git_commit: str


class FrozenDataDocument(BaseModel):
    """DVC/data-lineage identity frozen before the sealed test is accessed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    revision: str
    lineage_evidence_sha256: str
    dvc_lock_sha256: str
    source_archive_sha256: str
    role_datasets: dict[str, ArtifactDigestDocument]


class ReleaseDecisionDocument(BaseModel):
    """Serialized QA decision and ordered guardrail outcomes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str
    decision: str
    checks: dict[str, bool]

    @classmethod
    def from_domain(cls, decision: ReleaseDecision) -> ReleaseDecisionDocument:
        """Convert an immutable QA release decision into JSON evidence."""
        return cls(
            profile=decision.profile,
            decision=decision.decision.value,
            checks={check.value: passed for check, passed in decision.checks},
        )


class ModelBundleDocument(BaseModel):
    """Frozen model and metadata artifact identity with its MLflow model run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str
    model_path: str
    model_sha256: str
    metadata_path: str
    metadata_sha256: str
    mlflow_run_id: str


class ReleaseFreezeDocument(BaseModel):
    """Immutable pre-test evidence for one prepared model release."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[3]
    source: SourceRevisionDocument
    data: FrozenDataDocument
    configuration: dict[str, str]
    development_evidence: ArtifactDigestDocument
    feature_diagnostics: ArtifactDigestDocument | None = None
    development_decisions: tuple[ReleaseDecisionDocument, ...]
    model_bundles: tuple[ModelBundleDocument, ...]
    sealed_test: ArtifactDigestDocument


class ApprovedModelDocument(BaseModel):
    """The one candidate model permitted by a completed release decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str
    model_sha256: str
    metadata_sha256: str
    feature_contract_sha256: str
    model_mlflow_run_id: str
    final_mlflow_run_id: str


class HistoricalReconciliationDocument(BaseModel):
    """Scope an evidence migration that cannot recreate every original input blob."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    reason: Literal["serialized_bundle_and_metadata_integrity_contract"]
    original_release_freeze_sha256: str
    frozen_dvc_lock_sha256: str
    frozen_dvc_lock_snapshot_available: bool
    verified_test_dataset_sha256: str


class ReleaseManifestDocument(BaseModel):
    """Post-test release decision that links immutable freeze and model artifacts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    release_status: Literal["release_approved", "scenario_review"]
    deployment_allowed: bool
    approved_profile: str | None = None
    freeze_manifest: ArtifactDigestDocument
    canonical_evidence: ArtifactDigestDocument
    final_evidence: ArtifactDigestDocument
    decisions: tuple[ReleaseDecisionDocument, ...]
    model_bundles: dict[str, str]
    approved_model: ApprovedModelDocument | None = None
    historical_reconciliation: HistoricalReconciliationDocument | None = None


class BootstrapBundleDocument(BaseModel):
    """One bundle created from train/valid development evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_path: str
    model_sha256: str
    metadata_path: str
    metadata_sha256: str
    mlflow_run_id: str
    deployed: bool


class BootstrapManifestDocument(BaseModel):
    """Validated Model Trainer bootstrap artifact consumed before final evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    evaluation_role: Literal["valid"]
    accessed_roles: tuple[Literal["train", "valid"], Literal["train", "valid"]]
    bundles: dict[str, BootstrapBundleDocument]
    initial_deployed_profile: str
    candidate_deployment_allowed: bool
    candidate_deployment_reason: str
    provenance: dict[str, str]


class CanonicalSealedTestDocument(BaseModel):
    """Minimal canonical sealed-test state needed to block repeat execution."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    status: str


class CanonicalEvidenceDocument(BaseModel):
    """Minimal validated canonical evidence contract for lifecycle guards."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    sealed_test: CanonicalSealedTestDocument | None = None
    deployment_allowed: bool = False


class CanonicalReleaseSealedTestDocument(BaseModel):
    """Complete sealed-test identity written into new canonical release evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["evaluated_once"]
    artifact_sha256: str
    dataset_sha256: str
    accessed_roles: tuple[str, ...]
    freeze_manifest_path: str
    freeze_manifest_sha256: str


class CanonicalReleaseEvidenceDocument(BaseModel):
    """Validated canonical output written after one sealed-test evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    status: Literal["APPROVED", "SCENARIO_REVIEW_REQUIRED"]
    deployment_allowed: bool
    sealed_test: CanonicalReleaseSealedTestDocument
    profiles: tuple[dict[str, object], ...]
    decisions: tuple[ReleaseDecisionDocument, ...]
    configuration: dict[str, str]
    post_test_tuning_allowed: Literal[False]
