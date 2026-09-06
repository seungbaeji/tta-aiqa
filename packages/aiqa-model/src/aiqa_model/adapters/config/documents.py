"""Validated external DTOs for model profile and evaluation YAML documents."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from aiqa_model.domain import (
    EvaluationPlan,
    FeatureSelectionStrategy,
    FeatureSetCatalog,
    MetricName,
    ModelKind,
    ModelProfile,
    ModelProfileCatalog,
    ModelRole,
    SelectedFeatureSet,
)


class ProfileDocument(BaseModel):
    """One externally configured model profile before domain conversion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    model_role: ModelRole
    candidate_id: str | None = None
    kind: ModelKind
    threshold: float = Field(gt=0, lt=1)
    params: dict[str, Any]

    def to_domain(self) -> ModelProfile:
        """Convert the validated configuration into an immutable model profile."""
        return ModelProfile(
            name=self.name,
            model_role=self.model_role,
            candidate_id=self.candidate_id,
            kind=self.kind,
            threshold=self.threshold,
            params=tuple(sorted(self.params.items())),
        )


class ProfilesDocument(BaseModel):
    """Root DTO for one versioned model-profile configuration document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    random_seed: int
    profiles: tuple[ProfileDocument, ...] = Field(min_length=1)

    def to_domain(self) -> ModelProfileCatalog:
        """Convert profiles and their shared seed into a validated catalog."""
        return ModelProfileCatalog(
            random_seed=self.random_seed,
            profiles=tuple(profile.to_domain() for profile in self.profiles),
        )


class FeatureSetDocument(BaseModel):
    """One V1 or V2 feature-selection declaration before domain conversion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    selection: FeatureSelectionStrategy | None = None
    rationale: str | None = None
    description: str | None = None
    include: Literal["all"] | None = None
    exclude: tuple[str, ...] = ()

    def to_domain(self) -> SelectedFeatureSet:
        """Convert V1/V2 full-contract policy syntax into the common domain value."""
        if self.selection is not None:
            return SelectedFeatureSet(
                name=self.name,
                strategy=self.selection,
                rationale=self.rationale or self.description or "configured selection",
            )
        if self.include == "all" and not self.exclude:
            return SelectedFeatureSet(
                name=self.name,
                strategy=FeatureSelectionStrategy.ALL_FROM_MODEL_INPUT_CONTRACT,
                rationale=self.description or "legacy full feature selection",
            )
        raise ValueError("feature-set configuration uses an unsupported selection")


class FeatureSetsDocument(BaseModel):
    """Root DTO for V1/V2 versioned model feature-selection configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    canonical_feature_set: str | None = None
    default: str | None = None
    feature_sets: tuple[FeatureSetDocument, ...] = Field(min_length=1)

    def to_domain(self) -> FeatureSetCatalog:
        """Resolve legacy or current canonical name into a typed selection catalog."""
        canonical = self.canonical_feature_set or self.default
        if canonical is None:
            raise ValueError(
                "feature-set configuration requires a canonical feature set"
            )
        if (
            self.canonical_feature_set
            and self.default
            and self.canonical_feature_set != self.default
        ):
            raise ValueError("feature-set canonical names must not conflict")
        return FeatureSetCatalog(
            canonical_feature_set=canonical,
            feature_sets=tuple(item.to_domain() for item in self.feature_sets),
        )


class CrossValidationDocument(BaseModel):
    """External repeated cross-validation settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    splits: int = Field(ge=2)
    repeats: int = Field(ge=1)
    random_seed: int


class BootstrapDocument(BaseModel):
    """External deterministic bootstrap confidence-bound settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    iterations: int = Field(ge=1)
    confidence_level: float = Field(gt=0, lt=1)


class EvaluationDocument(BaseModel):
    """Root DTO for model evaluation settings and owned metric definitions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    cross_validation: CrossValidationDocument
    bootstrap: BootstrapDocument
    ranking_metrics: tuple[MetricName, ...] = Field(min_length=1)
    operating_metrics: tuple[MetricName, ...] = Field(min_length=1)

    def to_domain(self) -> EvaluationPlan:
        """Convert the validated evaluation policy into an immutable domain plan."""
        return EvaluationPlan(
            cv_splits=self.cross_validation.splits,
            cv_repeats=self.cross_validation.repeats,
            random_seed=self.cross_validation.random_seed,
            bootstrap_iterations=self.bootstrap.iterations,
            confidence_level=self.bootstrap.confidence_level,
            ranking_metrics=self.ranking_metrics,
            operating_metrics=self.operating_metrics,
        )
