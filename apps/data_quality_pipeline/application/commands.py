"""Explicit stage dispatch for Data Quality Pipeline delivery adapters."""

from collections.abc import Callable
from dataclasses import dataclass

from data_quality_pipeline.domain import DataPreparationResult, DataQualityStage


@dataclass(frozen=True)
class DataQualityOperations:
    """Named data preparation functions bound by the application composition root."""

    verify_source: Callable[[], DataPreparationResult]
    extract: Callable[[], DataPreparationResult]
    aggregate: Callable[[], DataPreparationResult]
    split: Callable[[], DataPreparationResult]
    revise_split: Callable[[], DataPreparationResult]
    validate: Callable[[], DataPreparationResult]


def execute_data_quality_stage(
    stage: DataQualityStage,
    *,
    operations: DataQualityOperations,
) -> DataPreparationResult:
    """Dispatch one validated stage to its explicitly bound use-case function."""
    if stage is DataQualityStage.VERIFY_SOURCE:
        return operations.verify_source()
    if stage is DataQualityStage.EXTRACT:
        return operations.extract()
    if stage is DataQualityStage.AGGREGATE:
        return operations.aggregate()
    if stage is DataQualityStage.SPLIT:
        return operations.split()
    if stage is DataQualityStage.REVISE_SPLIT:
        return operations.revise_split()
    if stage is DataQualityStage.VALIDATE:
        return operations.validate()
    raise ValueError(f"unsupported data-quality stage: {stage}")
