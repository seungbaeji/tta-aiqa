"""Deterministic traffic scenario values and invariants."""

from dataclasses import dataclass
from enum import StrEnum


class ScenarioMode(StrEnum):
    VALID = "valid"
    SHIFT = "shift"
    INVALID = "invalid"


@dataclass(frozen=True)
class FeatureTransform:
    feature: str
    add: float = 0.0
    multiply: float = 1.0
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class TrafficPlan:
    name: str
    mode: ScenarioMode
    request_count: int
    interval_seconds: float
    timeout_seconds: float
    transforms: tuple[FeatureTransform, ...] = ()
    invalid_cases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
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


@dataclass(frozen=True)
class TrafficResponse:
    request_id: str
    scenario: str
    status_code: int
    elapsed_seconds: float
    body: dict[str, object]
