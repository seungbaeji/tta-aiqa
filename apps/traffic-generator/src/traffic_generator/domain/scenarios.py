"""Deterministic traffic scenario values and invariants."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class ScenarioMode(StrEnum):
    """High-level behavior applied to one configured traffic scenario."""

    VALID = "valid"
    SHIFT = "shift"
    INVALID = "invalid"


class InvalidTrafficCase(StrEnum):
    """Intentional public API contract failures emitted by the invalid scenario."""

    MISSING_FEATURE = "missing_feature"
    EXTRA_FEATURE = "extra_feature"
    WRONG_BOOLEAN_TYPE = "wrong_boolean_type"


@dataclass(frozen=True)
class FeatureTransform:
    """One bounded numeric perturbation applied to a configured feature value."""

    feature: str
    add: float = 0.0
    multiply: float = 1.0
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        """Require finite numeric parameters and a coherent optional range."""
        if not self.feature or self.feature != self.feature.strip():
            raise ValueError("traffic transform feature must be non-empty and trimmed")
        values = (self.add, self.multiply, self.minimum, self.maximum)
        if any(value is not None and not isfinite(value) for value in values):
            raise ValueError("traffic transform values must be finite")
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError("traffic transform minimum must not exceed maximum")


@dataclass(frozen=True)
class TrafficPlan:
    """Validated request count, timing, and behavior for one named scenario."""

    name: str
    mode: ScenarioMode
    request_count: int
    interval_seconds: float
    timeout_seconds: float
    transforms: tuple[FeatureTransform, ...] = ()
    invalid_cases: tuple[InvalidTrafficCase, ...] = ()

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.strip():
            raise ValueError("traffic scenario name must be non-empty and trimmed")
        if (
            self.request_count < 1
            or self.interval_seconds < 0
            or self.timeout_seconds <= 0
        ):
            raise ValueError("traffic timing and count values are invalid")
        if self.mode is ScenarioMode.SHIFT and not self.transforms:
            raise ValueError("shift scenario requires transforms")
        if self.mode is ScenarioMode.INVALID and not self.invalid_cases:
            raise ValueError("invalid scenario requires invalid cases")
        if len(self.invalid_cases) != len(set(self.invalid_cases)):
            raise ValueError("invalid traffic cases must be unique")


@dataclass(frozen=True)
class TrafficResponse:
    """Captured response evidence from one request sent through a client port."""

    request_id: str
    scenario: str
    status_code: int
    elapsed_seconds: float
    body: dict[str, object]
