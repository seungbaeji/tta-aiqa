"""Pydantic DTOs for versioned model benchmark evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aiqa_model.domain import (
    BenchmarkResult,
    BinaryMetrics,
    FeatureCoefficient,
    FeatureDiagnostics,
    FeatureSelection,
    FeatureSummary,
    MetricDistribution,
    PermutationImportance,
    ProfileEvaluation,
)


class BinaryMetricsDocument(BaseModel):
    """Serialized thresholded and ranking metrics for one profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    true_negative: int
    false_positive: int
    false_negative: int
    true_positive: int

    @classmethod
    def from_domain(cls, metrics: BinaryMetrics) -> BinaryMetricsDocument:
        """Convert immutable domain metrics into their evidence DTO."""
        return cls(
            precision=metrics.precision,
            recall=metrics.recall,
            f1=metrics.f1,
            roc_auc=metrics.roc_auc,
            pr_auc=metrics.pr_auc,
            true_negative=metrics.true_negative,
            false_positive=metrics.false_positive,
            false_negative=metrics.false_negative,
            true_positive=metrics.true_positive,
        )

    def to_domain(self) -> BinaryMetrics:
        """Convert validated serialized metrics into the domain value."""
        return BinaryMetrics(
            precision=self.precision,
            recall=self.recall,
            f1=self.f1,
            roc_auc=self.roc_auc,
            pr_auc=self.pr_auc,
            true_negative=self.true_negative,
            false_positive=self.false_positive,
            false_negative=self.false_negative,
            true_positive=self.true_positive,
        )


class MetricDistributionDocument(BaseModel):
    """Serialized repeated-CV distribution for one configured metric."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mean: float
    standard_deviation: float

    @classmethod
    def from_domain(
        cls, distribution: MetricDistribution
    ) -> MetricDistributionDocument:
        """Convert immutable metric distribution into its evidence DTO."""
        return cls(
            mean=distribution.mean,
            standard_deviation=distribution.standard_deviation,
        )

    def to_domain(self) -> MetricDistribution:
        """Convert validated distribution data into the domain value."""
        return MetricDistribution(
            mean=self.mean,
            standard_deviation=self.standard_deviation,
        )


class ProfileEvaluationDocument(BaseModel):
    """Serialized evaluation evidence for one configured model profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str
    threshold: float
    metrics: BinaryMetricsDocument
    bootstrap_recall_lower: float
    cross_validation: dict[str, MetricDistributionDocument]

    @classmethod
    def from_domain(
        cls, evaluation: ProfileEvaluation
    ) -> ProfileEvaluationDocument:
        """Convert one profile evaluation into versioned JSON-compatible evidence."""
        return cls(
            profile=evaluation.profile,
            threshold=evaluation.threshold,
            metrics=BinaryMetricsDocument.from_domain(evaluation.metrics),
            bootstrap_recall_lower=evaluation.bootstrap_recall_lower,
            cross_validation={
                name: MetricDistributionDocument.from_domain(distribution)
                for name, distribution in evaluation.cross_validation
            },
        )

    def to_domain(self) -> ProfileEvaluation:
        """Convert validated profile evidence into its domain value."""
        return ProfileEvaluation(
            profile=self.profile,
            threshold=self.threshold,
            metrics=self.metrics.to_domain(),
            bootstrap_recall_lower=self.bootstrap_recall_lower,
            cross_validation=tuple(
                (name, distribution.to_domain())
                for name, distribution in self.cross_validation.items()
            ),
        )


class BenchmarkEvidenceDocument(BaseModel):
    """Root DTO for one versioned validation or sealed-test benchmark result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    evaluation_role: Literal["valid", "test"]
    accessed_roles: tuple[str, ...]
    profiles: tuple[ProfileEvaluationDocument, ...] = Field(min_length=1)

    @classmethod
    def from_domain(cls, result: BenchmarkResult) -> BenchmarkEvidenceDocument:
        """Convert a benchmark result into the canonical evidence DTO."""
        return cls(
            schema_version=1,
            evaluation_role=result.evaluation_role,
            accessed_roles=result.accessed_roles,
            profiles=tuple(
                ProfileEvaluationDocument.from_domain(profile)
                for profile in result.profiles
            ),
        )

    def to_domain(self) -> BenchmarkResult:
        """Convert validated benchmark evidence into the immutable domain result."""
        return BenchmarkResult(
            evaluation_role=self.evaluation_role,
            accessed_roles=self.accessed_roles,
            profiles=tuple(profile.to_domain() for profile in self.profiles),
        )


class FeatureSummaryDocument(BaseModel):
    """Serialized descriptive statistics for one canonical model input feature."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feature: str
    dtype: str
    missing_rate: float
    distinct_values: int
    variance: float | None
    target_correlation: float | None

    @classmethod
    def from_domain(cls, summary: FeatureSummary) -> FeatureSummaryDocument:
        """Convert one feature summary into its evidence DTO."""
        return cls(
            feature=summary.feature,
            dtype=summary.dtype,
            missing_rate=summary.missing_rate,
            distinct_values=summary.distinct_values,
            variance=summary.variance,
            target_correlation=summary.target_correlation,
        )


class FeatureCoefficientDocument(BaseModel):
    """Serialized ranked coefficient from the baseline profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feature: str
    coefficient: float

    @classmethod
    def from_domain(
        cls, coefficient: FeatureCoefficient
    ) -> FeatureCoefficientDocument:
        """Convert one baseline coefficient into its evidence DTO."""
        return cls(feature=coefficient.feature, coefficient=coefficient.coefficient)


class PermutationImportanceDocument(BaseModel):
    """Serialized candidate permutation-importance measurement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feature: str
    mean: float
    standard_deviation: float

    @classmethod
    def from_domain(
        cls, importance: PermutationImportance
    ) -> PermutationImportanceDocument:
        """Convert one permutation-importance measurement into its evidence DTO."""
        return cls(
            feature=importance.feature,
            mean=importance.mean,
            standard_deviation=importance.standard_deviation,
        )


class FeatureDiagnosticsEvidenceDocument(BaseModel):
    """Root DTO for development-only feature diagnostics evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    accessed_roles: tuple[str, ...]
    test_accessed: bool
    feature_count: int = Field(ge=0)
    selection: FeatureSelection
    features: tuple[FeatureSummaryDocument, ...]
    top_baseline_coefficients: tuple[FeatureCoefficientDocument, ...]
    candidate_permutation_importance: tuple[PermutationImportanceDocument, ...]

    @classmethod
    def from_domain(
        cls, result: FeatureDiagnostics
    ) -> FeatureDiagnosticsEvidenceDocument:
        """Convert feature diagnostics into the canonical evidence DTO."""
        return cls(
            schema_version=result.schema_version,
            accessed_roles=result.accessed_roles,
            test_accessed=result.test_accessed,
            feature_count=result.feature_count,
            selection=result.selection,
            features=tuple(
                FeatureSummaryDocument.from_domain(feature)
                for feature in result.features
            ),
            top_baseline_coefficients=tuple(
                FeatureCoefficientDocument.from_domain(coefficient)
                for coefficient in result.top_baseline_coefficients
            ),
            candidate_permutation_importance=tuple(
                PermutationImportanceDocument.from_domain(importance)
                for importance in result.candidate_permutation_importance
            ),
        )
