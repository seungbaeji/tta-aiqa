"""Pydantic DTOs for serialized sklearn model bundle metadata."""

from __future__ import annotations

from typing import Any, Literal

from aiqa_core.domain import FeatureSet
from pydantic import BaseModel, ConfigDict, Field

from aiqa_model.domain import ModelKind, ModelProfile, ModelRole, ProfileEvaluation


class FeatureDefinitionDocument(BaseModel):
    """Serialized feature definition embedded in one model bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    dtype: str
    nullable: bool


class FeatureContractDocument(BaseModel):
    """Versioned serving input contract embedded with a fitted model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    sha256: str
    features: tuple[FeatureDefinitionDocument, ...] = Field(min_length=1)


class ValidationMetricsDocument(BaseModel):
    """Validation metrics recorded with a serialized model profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    false_negative: int
    bootstrap_recall_lower: float


class ModelBundleMetadataDocument(BaseModel):
    """Complete external metadata contract paired with one joblib model artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    profile: str
    candidate_id: str | None = None
    model_role: ModelRole
    model_kind: ModelKind
    threshold: float
    params: dict[str, Any]
    target: str
    feature_contract: FeatureContractDocument
    validation_metrics: ValidationMetricsDocument
    provenance: dict[str, str]
    model_sha256: str | None = None

    @classmethod
    def from_domain(
        cls,
        *,
        profile: ModelProfile,
        evaluation: ProfileEvaluation,
        feature_set: FeatureSet,
        feature_contract_sha256: str,
        provenance: dict[str, str],
    ) -> ModelBundleMetadataDocument:
        """Create serializable bundle metadata from immutable model domain values."""
        return cls(
            schema_version=1,
            profile=profile.name,
            candidate_id=profile.candidate_id,
            model_role=profile.model_role,
            model_kind=profile.kind,
            threshold=profile.threshold,
            params=profile.parameter_dict(),
            target=feature_set.target,
            feature_contract=FeatureContractDocument(
                name=feature_set.name,
                sha256=feature_contract_sha256,
                features=tuple(
                    FeatureDefinitionDocument(
                        name=feature.name,
                        dtype=feature.dtype.value,
                        nullable=feature.nullable,
                    )
                    for feature in feature_set.features
                ),
            ),
            validation_metrics=ValidationMetricsDocument(
                precision=evaluation.metrics.precision,
                recall=evaluation.metrics.recall,
                f1=evaluation.metrics.f1,
                roc_auc=evaluation.metrics.roc_auc,
                pr_auc=evaluation.metrics.pr_auc,
                false_negative=evaluation.metrics.false_negative,
                bootstrap_recall_lower=evaluation.bootstrap_recall_lower,
            ),
            provenance=provenance,
        )

    def embedded_document(self) -> ModelBundleMetadataDocument:
        """Return the metadata representation stored inside the joblib payload."""
        return self.model_copy(update={"model_sha256": None})
