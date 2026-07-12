"""Model profile and evaluation domain values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ModelKind(StrEnum):
    """Supported model families in the classroom benchmark."""

    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"


class ModelRole(StrEnum):
    """Lifecycle role assigned to a configured model profile."""

    BASELINE = "baseline"
    CANDIDATE = "candidate"
    DEPLOYED = "deployed"


@dataclass(frozen=True)
class ModelProfile:
    """Immutable model family, threshold, and hyperparameter definition."""

    name: str
    model_role: ModelRole
    kind: ModelKind
    threshold: float
    params: tuple[tuple[str, object], ...]
    candidate_id: str | None = None

    def __post_init__(self) -> None:
        if not 0 < self.threshold < 1:
            raise ValueError("model threshold must be between zero and one")
        if self.model_role is ModelRole.CANDIDATE and not self.candidate_id:
            raise ValueError("candidate profile requires candidate_id")
        if self.model_role is not ModelRole.CANDIDATE and self.candidate_id:
            raise ValueError("non-candidate profile must not define candidate_id")

    def parameter_dict(self) -> dict[str, object]:
        """Return hyperparameters in the form expected by sklearn."""
        return dict(self.params)


@dataclass(frozen=True)
class EvaluationPlan:
    """Cross-validation and bootstrap settings for one model revision."""

    cv_splits: int
    cv_repeats: int
    random_seed: int
    bootstrap_iterations: int
    confidence_level: float

    def __post_init__(self) -> None:
        if self.cv_splits < 2 or self.cv_repeats < 1:
            raise ValueError("cross-validation configuration is invalid")
        if self.bootstrap_iterations < 1:
            raise ValueError("bootstrap iterations must be positive")
        if not 0 < self.confidence_level < 1:
            raise ValueError("confidence level must be between zero and one")


@dataclass(frozen=True)
class BinaryMetrics:
    """Thresholded classification and probability-ranking measurements."""

    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    true_negative: int
    false_positive: int
    false_negative: int
    true_positive: int


@dataclass(frozen=True)
class MetricDistribution:
    """Summary statistics for a metric over validation folds."""

    mean: float
    standard_deviation: float


@dataclass(frozen=True)
class ProfileEvaluation:
    """Evaluation result for one model profile and one dataset role."""

    profile: str
    threshold: float
    metrics: BinaryMetrics
    bootstrap_recall_lower: float
    cross_validation: tuple[tuple[str, MetricDistribution], ...]


class FeatureSelection(StrEnum):
    """Supported feature-selection outcomes for the course benchmark."""

    RETAIN_ALL_CANONICAL = "retain_all_canonical_features"


@dataclass(frozen=True)
class FeatureSummary:
    """Descriptive statistics for one model input feature."""

    feature: str
    dtype: str
    missing_rate: float
    distinct_values: int
    variance: float | None
    target_correlation: float | None


@dataclass(frozen=True)
class FeatureCoefficient:
    """One ranked coefficient from the baseline preprocessor."""

    feature: str
    coefficient: float


@dataclass(frozen=True)
class PermutationImportance:
    """Validation permutation importance for one canonical feature."""

    feature: str
    mean: float
    standard_deviation: float


@dataclass(frozen=True)
class FeatureDiagnostics:
    """Typed feature diagnostics produced without accessing the sealed test role."""

    schema_version: int
    accessed_roles: tuple[str, ...]
    test_accessed: bool
    feature_count: int
    selection: FeatureSelection
    features: tuple[FeatureSummary, ...]
    top_baseline_coefficients: tuple[FeatureCoefficient, ...]
    candidate_permutation_importance: tuple[PermutationImportance, ...]

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("feature diagnostics schema version must be positive")
        if self.accessed_roles != ("train", "valid") or self.test_accessed:
            raise ValueError("feature diagnostics must use train and valid roles only")
        if self.feature_count != len(self.features):
            raise ValueError("feature diagnostics count does not match summaries")


@dataclass(frozen=True)
class BenchmarkResult:
    """Complete benchmark result with explicit role-access provenance."""

    evaluation_role: str
    accessed_roles: tuple[str, ...]
    profiles: tuple[ProfileEvaluation, ...]

    def __post_init__(self) -> None:
        if self.evaluation_role not in {"valid", "test"}:
            raise ValueError("benchmark evaluation role must be valid or test")
        if not self.profiles:
            raise ValueError("benchmark result requires profile evaluations")
        names = [profile.profile for profile in self.profiles]
        if len(names) != len(set(names)):
            raise ValueError("benchmark profile evaluations must be unique")
