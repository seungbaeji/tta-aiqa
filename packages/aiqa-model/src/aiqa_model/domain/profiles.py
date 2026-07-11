"""Model profile and evaluation domain values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from aiqa_core.domain import ModelRole


class ModelKind(StrEnum):
    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"


@dataclass(frozen=True)
class ModelProfile:
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
        return dict(self.params)


@dataclass(frozen=True)
class EvaluationPlan:
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
    mean: float
    standard_deviation: float


@dataclass(frozen=True)
class ProfileEvaluation:
    profile: str
    threshold: float
    metrics: BinaryMetrics
    bootstrap_recall_lower: float
    cross_validation: tuple[tuple[str, MetricDistribution], ...]


@dataclass(frozen=True)
class BenchmarkResult:
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
