"""Raw patient record domain values."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    """One timestamped raw measurement for a patient record."""

    minute: int
    parameter: str
    value: float

    def __post_init__(self) -> None:
        if self.minute < 0:
            raise ValueError("observation minute must not be negative")
        if not self.parameter or self.parameter.strip() != self.parameter:
            raise ValueError("observation parameter must be non-empty and trimmed")


@dataclass(frozen=True)
class PatientRecord:
    """All raw observations associated with one source patient record."""

    record_id: int
    observations: tuple[Observation, ...]

    def __post_init__(self) -> None:
        if self.record_id < 1:
            raise ValueError("patient record ID must be positive")
        if not isinstance(self.observations, tuple):
            raise ValueError("patient observations must be immutable")
