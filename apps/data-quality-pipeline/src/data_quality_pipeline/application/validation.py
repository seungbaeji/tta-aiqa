"""Great Expectations validation use case for prepared data artifacts."""

from data_quality_pipeline.domain import (
    DataPreparationResult,
    DataQualityPaths,
    DataQualityStage,
)
from data_quality_pipeline.ports import QualityValidator


def validate_quality(
    paths: DataQualityPaths,
    *,
    validator: QualityValidator | None,
) -> DataPreparationResult:
    """Run configured quality checks and return a non-blocking evidence outcome."""
    if paths.quality_rules_path is None or paths.validation_artifact_dir is None:
        raise ValueError(
            "validate requires quality rules and validation artifact paths"
        )
    if validator is None:
        raise ValueError("validate requires a configured quality validator")
    return DataPreparationResult(
        command=DataQualityStage.VALIDATE,
        success=validator.validate(
            paths.patient_features_path,
            paths.validation_artifact_dir,
        ),
    )
