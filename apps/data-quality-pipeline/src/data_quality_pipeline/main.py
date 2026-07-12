"""CLI entry point for data preparation and validation."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from data_quality_pipeline.bootstrap import bootstrap
from data_quality_pipeline.settings import DataQualitySettings
from data_quality_pipeline.workflow import DataPreparationResult, DataQualityStage

CLI_STAGES = (
    DataQualityStage.VERIFY_SOURCE,
    DataQualityStage.EXTRACT,
    DataQualityStage.AGGREGATE,
    DataQualityStage.SPLIT,
    DataQualityStage.VALIDATE,
)


class DataQualityCliDto(BaseModel):
    """Validated external CLI input for one data-quality workflow stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: DataQualityStage
    source_contract: Path
    aggregation_config: Path
    split_config: Path
    patient_features: Path
    split_manifest: Path
    split_dataset_dir: Path
    source_evidence: Path
    quality_rules: Path | None = None
    validation_artifact_dir: Path | None = None

    def to_settings(self) -> DataQualitySettings:
        """Convert CLI DTO values into runtime settings for the composition root."""
        return DataQualitySettings(
            source_contract_path=self.source_contract,
            aggregation_config_path=self.aggregation_config,
            split_config_path=self.split_config,
            patient_features_path=self.patient_features,
            split_manifest_path=self.split_manifest,
            split_dataset_dir=self.split_dataset_dir,
            source_evidence_path=self.source_evidence,
            quality_rules_path=self.quality_rules,
            validation_artifact_dir=self.validation_artifact_dir,
        )


class DataQualityValidationFailed(RuntimeError):
    """Signal a completed validation command whose quality checks did not pass."""


def parse_args() -> DataQualityCliDto:
    """Parse and validate one external data-quality CLI command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=tuple(stage.value for stage in CLI_STAGES))
    parser.add_argument("--source-contract", required=True)
    parser.add_argument("--aggregation-config", required=True)
    parser.add_argument("--split-config", required=True)
    parser.add_argument("--patient-features", required=True)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--split-dataset-dir", required=True)
    parser.add_argument("--source-evidence", required=True)
    parser.add_argument("--quality-rules")
    parser.add_argument("--validation-artifact-dir")
    return DataQualityCliDto.model_validate(vars(parser.parse_args()))


def main() -> None:
    """Invoke the bound stage operation and render its JSON outcome."""
    command = parse_args()
    runtime = bootstrap(command.to_settings())
    failed = False
    result: DataPreparationResult
    try:
        with runtime.telemetry.run_scope(
            f"data_quality.{command.stage}",
            attributes={"command": command.stage},
        ):
            result = runtime.run(command.stage)
            result_attributes = {
                name: value
                for name, value in asdict(result).items()
                if value is not None
            }
            if result.success is False:
                runtime.telemetry.event(
                    "data_quality.command.failed",
                    level=logging.ERROR,
                    attributes=result_attributes,
                )
                raise DataQualityValidationFailed(
                    "data quality validation did not pass"
                )
            runtime.telemetry.event(
                "data_quality.command.completed", attributes=result_attributes
            )
    except DataQualityValidationFailed:
        failed = True
    finally:
        runtime.telemetry.shutdown()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
