"""Data preparation outbound ports."""

from collections.abc import Iterable, Mapping
from typing import Protocol

from aiqa_data.domain import PatientRecord, SplitAssignment


class PatientRecordRepository(Protocol):
    def records(self) -> Iterable[PatientRecord]: ...


class OutcomeRepository(Protocol):
    def outcomes(self) -> Mapping[int, int]: ...


class SplitStrategy(Protocol):
    def assign(self, targets: Mapping[int, int]) -> tuple[SplitAssignment, ...]: ...
