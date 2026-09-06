"""CSV dataset readers that enforce the canonical model-input contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from aiqa_core.domain import FeatureSet

from aiqa_model.domain import ModelDatasetRole


@dataclass(frozen=True)
class DevelopmentData:
    """Pandas frames available to development-only model capabilities."""

    train: pd.DataFrame
    valid: pd.DataFrame


class CsvModelDatasetReader:
    """Read labeled model datasets from one deterministic split directory."""

    def __init__(self, dataset_dir: Path, feature_set: FeatureSet) -> None:
        self._dataset_dir = dataset_dir
        self._feature_set = feature_set

    def read_development(self) -> DevelopmentData:
        """Return validated train and valid frames without opening the sealed test."""
        return DevelopmentData(
            train=read_labeled_dataset(
                self._dataset_dir / f"{ModelDatasetRole.TRAIN.value}.csv",
                self._feature_set,
                ModelDatasetRole.TRAIN,
            ),
            valid=read_labeled_dataset(
                self._dataset_dir / f"{ModelDatasetRole.VALID.value}.csv",
                self._feature_set,
                ModelDatasetRole.VALID,
            ),
        )

    def read_fitting_data(self) -> pd.DataFrame:
        """Return frozen train/valid rows used to fit persisted model bundles."""
        development = self.read_development()
        return pd.concat([development.train, development.valid], ignore_index=True)

    def read_sealed_test(self) -> pd.DataFrame:
        """Return a validated test frame for a confirmed final evaluation."""
        return read_labeled_dataset(
            self._dataset_dir / f"{ModelDatasetRole.TEST.value}.csv",
            self._feature_set,
            ModelDatasetRole.TEST,
        )


def read_labeled_dataset(
    path: Path,
    feature_set: FeatureSet,
    role: ModelDatasetRole,
) -> pd.DataFrame:
    """Read one labeled CSV role and reject any contract mismatch before modeling."""
    frame = pd.read_csv(path)
    expected_features = set(feature_set.feature_names)
    actual_features = set(frame.columns) - {"record_id", "target"}
    if actual_features != expected_features:
        raise ValueError(
            "model input contract mismatch: "
            f"missing={sorted(expected_features - actual_features)}, "
            f"extra={sorted(actual_features - expected_features)}"
        )
    if "record_id" in expected_features or feature_set.target in expected_features:
        raise ValueError("identifier or target leaked into model input contract")
    if "target" not in frame:
        raise ValueError(f"target missing from model dataset role: {role.value}")
    return frame
