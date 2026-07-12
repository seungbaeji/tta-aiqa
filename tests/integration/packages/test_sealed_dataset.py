"""Sealed model dataset access tests."""

from pathlib import Path

import pandas as pd
import pytest
from aiqa_core.domain import FeatureDefinition, FeatureSet, FeatureType
from aiqa_model.adapters import SklearnBenchmark
from aiqa_model.domain import (
    EvaluationPlan,
    MetricName,
    ModelKind,
    ModelProfile,
    ModelProfileSelection,
    ModelRole,
)
from aiqa_model.ports import FittedModels


def benchmark(dataset_dir: Path) -> SklearnBenchmark:
    return SklearnBenchmark(
        dataset_dir=dataset_dir,
        feature_set=FeatureSet(
            schema_version=1,
            name="test",
            target="target",
            features=(FeatureDefinition("value", FeatureType.FLOAT, False),),
        ),
        profiles=(
            ModelProfile(
                name="baseline",
                model_role=ModelRole.BASELINE,
                kind=ModelKind.LOGISTIC_REGRESSION,
                threshold=0.5,
                params=(),
            ),
        ),
        evaluation_plan=EvaluationPlan(
            cv_splits=2,
            cv_repeats=1,
            random_seed=42,
            bootstrap_iterations=10,
            confidence_level=0.95,
            ranking_metrics=(MetricName.PR_AUC, MetricName.ROC_AUC),
            operating_metrics=(
                MetricName.PRECISION,
                MetricName.RECALL,
                MetricName.F1,
                MetricName.CONFUSION_MATRIX,
            ),
        ),
        random_seed=42,
    )


class FittedPipeline:
    def predict_proba(self, values: pd.DataFrame):
        assert list(values.columns) == ["value"]
        return __import__("numpy").array(
            [[0.9, 0.1], [0.1, 0.9], [0.8, 0.2], [0.2, 0.8]]
        )


def test_final_evaluation_scores_supplied_serialized_pipeline(
    tmp_path: Path,
) -> None:
    pd.DataFrame(
        {
            "record_id": [1, 2, 3, 4],
            "value": [0.0, 1.0, 0.1, 0.9],
            "target": [0, 1, 0, 1],
        }
    ).to_csv(tmp_path / "test.csv", index=False)

    result = benchmark(tmp_path).evaluate_frozen_models(
        ModelProfileSelection.from_names(("baseline",)),
        FittedModels((("baseline", FittedPipeline()),)),
    )

    assert result.profiles[0].metrics.recall == pytest.approx(1.0)
    assert result.profiles[0].metrics.precision == pytest.approx(1.0)


def test_final_evaluation_rejects_an_unmatched_frozen_model_set(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="benchmark profiles"):
        benchmark(tmp_path).evaluate_frozen_models(
            ModelProfileSelection.from_names(("baseline",)),
            FittedModels.from_mapping({"candidate-b": FittedPipeline()}),
        )
