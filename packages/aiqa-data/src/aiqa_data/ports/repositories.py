"""Data preparation outbound ports."""

from collections.abc import Iterable, Mapping
from typing import Protocol

from aiqa_data.domain import PatientRecord, SplitAssignment


class PatientRecordRepository(Protocol):
    """Load raw patient records for a data-preparation use case."""

    def records(self) -> Iterable[PatientRecord]:
        """Yield all patient records available to the use case."""
        ...


class OutcomeRepository(Protocol):
    """Load binary patient outcomes for a data-preparation use case."""

    def outcomes(self) -> Mapping[int, int]:
        """Return source outcomes keyed by patient record ID."""
        ...


class SplitStrategy(Protocol):
    """Assign patient IDs to deterministic dataset roles."""

    def assign(self, targets: Mapping[int, int]) -> tuple[SplitAssignment, ...]:
        """Return one role assignment for every supplied patient ID."""
        ...
