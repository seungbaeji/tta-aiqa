"""Target-free patient CSV traffic pool adapter."""

from pathlib import Path

import pandas as pd
from aiqa_core.domain import FeatureSet, FeatureType


class CsvPatientPool:
    def __init__(self, path: Path, feature_set: FeatureSet) -> None:
        frame = pd.read_csv(path)
        if "target" in frame.columns:
            raise ValueError("traffic pool must not contain target")
        expected = {"record_id", *feature_set.feature_names}
        if set(frame.columns) != expected:
            raise ValueError("traffic pool does not match the feature contract")
        self._patients = tuple(
            {
                feature.name: _wire_value(row[feature.name], feature.dtype)
                for feature in feature_set.features
            }
            for _, row in frame.iterrows()
        )
        if not self._patients:
            raise ValueError("traffic pool is empty")

    @property
    def size(self) -> int:
        return len(self._patients)

    def patient(self, index: int) -> dict[str, object]:
        return dict(self._patients[index])


def _wire_value(value: object, dtype: FeatureType) -> object:
    if pd.isna(value):
        return None
    if dtype is FeatureType.BOOLEAN:
        return bool(int(float(value)))
    if dtype is FeatureType.INTEGER:
        return int(float(value))
    if dtype is FeatureType.FLOAT:
        return float(value)
    return float(value) if isinstance(value, int | float) else str(value)
