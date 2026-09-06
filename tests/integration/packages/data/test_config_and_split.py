"""V1 feature contract and deterministic split tests."""

from pathlib import Path

from aiqa_data.adapters import (
    SklearnStratifiedSplitStrategy,
    StratifiedSplitConfig,
    load_aggregation_plan,
)
from aiqa_data.domain import DatasetRole


def test_v1_aggregation_defines_133_available_features() -> None:
    plan = load_aggregation_plan(Path("configs/data/aggregation.yaml"))

    assert len(plan.feature_names) == 133
    assert len(set(plan.feature_names)) == 133
    assert "heart_rate__mean" in plan.feature_names
    assert "urine__sum" in plan.feature_names
    assert "mechanical_ventilation__missing" in plan.feature_names


def test_split_is_exact_stratified_and_deterministic() -> None:
    targets = {record_id: int(record_id < 554) for record_id in range(4000)}
    strategy = SklearnStratifiedSplitStrategy(
        StratifiedSplitConfig(
            random_seed=42,
            train_ratio=0.60,
            valid_ratio=0.15,
            test_ratio=0.15,
            operational_ratio=0.10,
        )
    )

    first = strategy.assign(targets)
    second = strategy.assign(targets)

    assert first == second
    counts = {role: sum(item.role is role for item in first) for role in DatasetRole}
    assert counts == {
        DatasetRole.TRAIN: 2400,
        DatasetRole.VALID: 600,
        DatasetRole.TEST: 600,
        DatasetRole.OPERATIONAL: 400,
    }
