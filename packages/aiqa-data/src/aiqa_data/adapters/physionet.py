"""PhysioNet 2012 filesystem and CSV adapters."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path

from aiqa_data.domain import Observation, PatientRecord

EXPECTED_RECORD_HEADER = ["Time", "Parameter", "Value"]
RECORD_ID_PARAMETER = "RecordID"


class PhysioNetRecordRepository:
    def __init__(
        self, records_dir: Path, expected_count: int, observation_window_hours: int
    ) -> None:
        self._records_dir = records_dir
        self._expected_count = expected_count
        self._max_minute = observation_window_hours * 60

    def records(self) -> Iterable[PatientRecord]:
        paths = sorted(self._records_dir.glob("*.txt"))
        if len(paths) != self._expected_count:
            raise ValueError(
                f"expected {self._expected_count} patient files, got {len(paths)}"
            )
        for path in paths:
            yield parse_record(path, max_minute=self._max_minute)


class PhysioNetOutcomeRepository:
    def __init__(
        self,
        path: Path,
        *,
        target_column: str,
        blocked_columns: tuple[str, ...],
    ) -> None:
        self._path = path
        self._target_column = target_column
        self._blocked_columns = blocked_columns

    def outcomes(self) -> Mapping[int, int]:
        with self._path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            columns = set(reader.fieldnames or [])
            required = {
                RECORD_ID_PARAMETER,
                self._target_column,
                *self._blocked_columns,
            }
            if missing := required - columns:
                raise ValueError(f"outcome columns missing: {sorted(missing)}")
            outcomes: dict[int, int] = {}
            for row in reader:
                record_id = int(row[RECORD_ID_PARAMETER])
                target = int(row[self._target_column])
                if target not in {0, 1}:
                    raise ValueError(
                        f"invalid target for patient {record_id}: {target}"
                    )
                if record_id in outcomes:
                    raise ValueError(f"duplicate outcome: {record_id}")
                outcomes[record_id] = target
        return outcomes


def parse_record(path: Path, *, max_minute: int | None = None) -> PatientRecord:
    record_id: int | None = None
    observations: list[Observation] = []
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != EXPECTED_RECORD_HEADER:
            raise ValueError(f"unexpected patient record header: {reader.fieldnames}")
        for row in reader:
            minute = parse_time(row["Time"])
            if max_minute is not None and minute > max_minute:
                raise ValueError(
                    f"observation exceeds configured window: {row['Time']}"
                )
            parameter = row["Parameter"]
            value = float(row["Value"])
            if parameter == RECORD_ID_PARAMETER:
                record_id = int(value)
            else:
                observations.append(Observation(minute, parameter, value))
    if record_id is None:
        raise ValueError(f"RecordID missing from patient file: {path}")
    if path.stem != str(record_id):
        raise ValueError(f"filename and RecordID differ: {path.stem} != {record_id}")
    return PatientRecord(record_id=record_id, observations=tuple(observations))


def parse_time(value: str) -> int:
    hours, minutes = (int(part) for part in value.split(":"))
    if hours < 0 or not 0 <= minutes < 60:
        raise ValueError(f"invalid PhysioNet time: {value}")
    return hours * 60 + minutes
