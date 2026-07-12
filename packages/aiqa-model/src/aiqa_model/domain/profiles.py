"""Model profile and evaluation domain values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from aiqa_model.domain.lifecycle import (
    DEVELOPMENT_DATASET_ROLES,
    FINALIZATION_DATASET_ROLES,
)


class ModelKind(StrEnum):
    """Supported model families in the classroom benchmark."""

    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"


class ModelRole(StrEnum):
    """Lifecycle role assigned to a configured model profile."""

    BASELINE = "baseline"
    CANDIDATE = "candidate"
    DEPLOYED = "deployed"


class MetricName(StrEnum):
    """Metrics allowed by the versioned model evaluation contract."""

    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    ROC_AUC = "roc_auc"
    PR_AUC = "pr_auc"
    CONFUSION_MATRIX = "confusion_matrix"


CROSS_VALIDATION_METRIC_ORDER = (
    MetricName.PRECISION,
    MetricName.RECALL,
    MetricName.F1,
    MetricName.ROC_AUC,
    MetricName.PR_AUC,
)


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
        if (
            not isinstance(self.name, str)
            or not self.name
            or self.name != self.name.strip()
        ):
            raise ValueError("model profile name must be a non-empty trimmed string")
        if not isinstance(self.model_role, ModelRole):
            raise ValueError("model profile role must be a ModelRole")
        if not isinstance(self.kind, ModelKind):
            raise ValueError("model profile kind must be a ModelKind")
        if not isinstance(self.threshold, float) or isinstance(self.threshold, bool):
            raise ValueError("model threshold must be a float")
        if not 0 < self.threshold < 1:
            raise ValueError("model threshold must be between zero and one")
        if not isinstance(self.params, tuple):
            raise ValueError("model parameters must be an immutable tuple")
        if any(
            not isinstance(item, tuple) or len(item) != 2 for item in self.params
        ):
            raise ValueError("model parameters must contain name-value pairs")
        parameter_names = tuple(name for name, _ in self.params)
        if any(
            not isinstance(name, str) or not name or name != name.strip()
            for name in parameter_names
        ):
            raise ValueError("model parameter names must be non-empty trimmed strings")
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("model parameter names must be unique")
        if self.model_role is ModelRole.CANDIDATE and not self.candidate_id:
            raise ValueError("candidate profile requires candidate_id")
        if self.model_role is not ModelRole.CANDIDATE and self.candidate_id:
            raise ValueError("non-candidate profile must not define candidate_id")
        if self.candidate_id is not None and (
            not isinstance(self.candidate_id, str)
            or self.candidate_id != self.candidate_id.strip()
        ):
            raise ValueError("candidate id must be a trimmed string")

    def parameter_dict(self) -> dict[str, object]:
        """Return hyperparameters in the form expected by sklearn."""
        return dict(self.params)


@dataclass(frozen=True)
class ModelProfileCatalog:
    """Versioned set of configured model profiles with one shared random seed."""

    random_seed: int
    profiles: tuple[ModelProfile, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.random_seed, int) or isinstance(self.random_seed, bool):
            raise ValueError("model profile catalog random seed must be an integer")
        if not isinstance(self.profiles, tuple) or not self.profiles:
            raise ValueError("model profile catalog requires at least one profile")
        if any(not isinstance(profile, ModelProfile) for profile in self.profiles):
            raise ValueError("model profile catalog contains an invalid profile")
        names = tuple(profile.name for profile in self.profiles)
        if len(names) != len(set(names)):
            raise ValueError("model profile catalog names must be unique")


@dataclass(frozen=True)
class EvaluationPlan:
    """Cross-validation and bootstrap settings for one model revision."""

    cv_splits: int
    cv_repeats: int
    random_seed: int
    bootstrap_iterations: int
    confidence_level: float
    ranking_metrics: tuple[MetricName, ...]
    operating_metrics: tuple[MetricName, ...]

    def __post_init__(self) -> None:
        if self.cv_splits < 2 or self.cv_repeats < 1:
            raise ValueError("cross-validation configuration is invalid")
        if self.bootstrap_iterations < 1:
            raise ValueError("bootstrap iterations must be positive")
        if not 0 < self.confidence_level < 1:
            raise ValueError("confidence level must be between zero and one")
        metric_groups = (self.ranking_metrics, self.operating_metrics)
        if any(not isinstance(group, tuple) or not group for group in metric_groups):
            raise ValueError("evaluation metric groups must be non-empty tuples")
        metrics = (*self.ranking_metrics, *self.operating_metrics)
        if any(not isinstance(metric, MetricName) for metric in metrics):
            raise ValueError("evaluation metrics must be MetricName values")
        if len(metrics) != len(set(metrics)):
            raise ValueError("evaluation metrics must not be duplicated across groups")
        if not any(metric in CROSS_VALIDATION_METRIC_ORDER for metric in metrics):
            raise ValueError("evaluation metrics must include a scoring metric")

    @property
    def cross_validation_metric_names(self) -> tuple[str, ...]:
        """Return configured scoring metrics in deterministic evidence order."""
        configured = {*self.ranking_metrics, *self.operating_metrics}
        return tuple(
            metric.value
            for metric in CROSS_VALIDATION_METRIC_ORDER
            if metric in configured
        )


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
        if self.accessed_roles != DEVELOPMENT_DATASET_ROLES or self.test_accessed:
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
        expected_roles = {
            "valid": DEVELOPMENT_DATASET_ROLES,
            "test": FINALIZATION_DATASET_ROLES,
        }
        if self.evaluation_role not in expected_roles:
            raise ValueError("benchmark evaluation role must be valid or test")
        if self.accessed_roles != expected_roles[self.evaluation_role]:
            raise ValueError(
                "benchmark role access does not match the evaluation stage"
            )
        if not self.profiles:
            raise ValueError("benchmark result requires profile evaluations")
        names = [profile.profile for profile in self.profiles]
        if len(names) != len(set(names)):
            raise ValueError("benchmark profile evaluations must be unique")
