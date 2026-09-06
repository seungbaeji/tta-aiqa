"""Target-free patient CSV traffic pool adapter."""

from pathlib import Path

import pandas as pd
from aiqa_core.domain import FeatureSet

from traffic_generator.adapters.wire_values import to_wire_value


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
        self._patients = tuple(
            {
                feature.name: to_wire_value(row[feature.name], feature.dtype)
                for feature in feature_set.features
            }
            for _, row in frame.iterrows()
        )
        if not self._patients:
            raise ValueError("traffic pool is empty")

    @property
    def size(self) -> int:
        """Return the number of available operational patient payloads."""
        return len(self._patients)

    def patient(self, index: int) -> dict[str, object]:
        """Return a defensive copy of one deterministic patient payload by index."""
        return dict(self._patients[index])
