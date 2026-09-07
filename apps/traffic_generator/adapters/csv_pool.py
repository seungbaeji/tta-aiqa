"""Target-free patient CSV traffic pool adapter."""

from pathlib import Path

import pandas as pd
from aiqa_core.domain import FeatureSet
from aiqa_observability import is_valid_correlation_id

from traffic_generator.adapters.wire_values import to_wire_value


def _record_id_from_row(value: object) -> str:
    """Keep CSV record identity as a bounded correlation token, not a feature."""
    if isinstance(value, bool) or value is None:
        raise ValueError("traffic pool record_id is invalid")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("traffic pool record_id is invalid")
        token = str(int(value))
    elif isinstance(value, int):
        token = str(value)
    else:
        token = str(value).strip()
    if not is_valid_correlation_id(token):
        raise ValueError("traffic pool record_id is invalid")
    return token


class CsvPatientPool:
    """Load a target-free operational patient pool matched to one feature contract."""

    def __init__(self, path: Path, feature_set: FeatureSet) -> None:
        """Validate and convert CSV rows into an immutable in-memory payload pool."""
        frame = pd.read_csv(path)
        if "target" in frame.columns:
            raise ValueError("traffic pool must not contain target")
        expected = {"record_id", *feature_set.feature_names}
        if set(frame.columns) != expected:
            raise ValueError("traffic pool does not match the feature contract")
        patients: list[tuple[str, dict[str, object]]] = []
        for _, row in frame.iterrows():
            patients.append(
                (
                    _record_id_from_row(row["record_id"]),
                    {
                        feature.name: to_wire_value(row[feature.name], feature.dtype)
                        for feature in feature_set.features
                    },
                )
            )
        if not patients:
            raise ValueError("traffic pool is empty")
        self._patients = tuple(patients)

    @property
    def size(self) -> int:
        """Return the number of available operational patient payloads."""
        return len(self._patients)

    def patient(self, index: int) -> dict[str, object]:
        """Return a defensive copy of one deterministic patient payload by index."""
        return dict(self._patients[index][1])

    def record_id(self, index: int) -> str:
        """Return the CSV record identity for one pool index without model features."""
        return self._patients[index][0]
