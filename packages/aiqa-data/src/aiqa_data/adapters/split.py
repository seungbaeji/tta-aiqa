"""Deterministic stratified patient split adapter."""

from dataclasses import dataclass

from sklearn.model_selection import train_test_split

from aiqa_data.domain import DatasetRole, SplitAssignment


@dataclass(frozen=True)
class StratifiedSplitConfig:
    random_seed: int
    train_ratio: float
    valid_ratio: float
    test_ratio: float
    operational_ratio: float

    def __post_init__(self) -> None:
        total = self.train_ratio + self.valid_ratio + self.test_ratio
        total += self.operational_ratio
        if abs(total - 1.0) > 1e-9:
            raise ValueError("split ratios must sum to one")
        if (
            min(
                self.train_ratio,
                self.valid_ratio,
                self.test_ratio,
                self.operational_ratio,
            )
            <= 0
        ):
            raise ValueError("split ratios must be positive")


class SklearnStratifiedSplitStrategy:
    def __init__(self, config: StratifiedSplitConfig) -> None:
        self._config = config

    def assign(self, targets: dict[int, int]) -> tuple[SplitAssignment, ...]:
        ids = sorted(targets)
        labels = [targets[record_id] for record_id in ids]
        development_ids, operational_ids = train_test_split(
            ids,
            test_size=self._config.operational_ratio,
            random_state=self._config.random_seed,
            stratify=labels,
        )
        development_labels = [targets[record_id] for record_id in development_ids]
        test_fraction = self._config.test_ratio / (
            self._config.train_ratio
            + self._config.valid_ratio
            + self._config.test_ratio
        )
        train_valid_ids, test_ids = train_test_split(
            development_ids,
            test_size=test_fraction,
            random_state=self._config.random_seed,
            stratify=development_labels,
        )
        train_valid_labels = [targets[record_id] for record_id in train_valid_ids]
        valid_fraction = self._config.valid_ratio / (
            self._config.train_ratio + self._config.valid_ratio
        )
        train_ids, valid_ids = train_test_split(
            train_valid_ids,
            test_size=valid_fraction,
            random_state=self._config.random_seed,
            stratify=train_valid_labels,
        )
        roles = {
            **{record_id: DatasetRole.TRAIN for record_id in train_ids},
            **{record_id: DatasetRole.VALID for record_id in valid_ids},
            **{record_id: DatasetRole.TEST for record_id in test_ids},
            **{record_id: DatasetRole.OPERATIONAL for record_id in operational_ids},
        }
        return tuple(
            SplitAssignment(record_id=record_id, role=roles[record_id])
            for record_id in sorted(ids)
        )
