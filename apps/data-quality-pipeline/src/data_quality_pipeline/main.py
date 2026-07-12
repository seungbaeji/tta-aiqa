"""CLI entry point for data preparation and validation."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable
from dataclasses import asdict

from aiqa_observability import create_telemetry, load_telemetry_policy

from data_quality_pipeline.bootstrap import (
    DataPreparationResult,
    aggregate,
    extract_source,
    split,
    verify_source,
)
from data_quality_pipeline.settings import DataQualitySettings
from data_quality_pipeline.validation import validate

COMMANDS: dict[str, Callable[[DataQualitySettings], DataPreparationResult]] = {
    "verify-source": verify_source,
    "extract": extract_source,
    "aggregate": aggregate,
    "split": split,
    "validate": validate,
}


class DataQualityValidationFailed(RuntimeError):
    """Signal a completed validation command whose quality checks did not pass."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=tuple(COMMANDS))
    parser.add_argument("--source-contract", required=True)
    parser.add_argument("--aggregation-config", required=True)
    parser.add_argument("--split-config", required=True)
    parser.add_argument("--patient-features", required=True)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--split-dataset-dir", required=True)
    parser.add_argument("--source-evidence", required=True)
    parser.add_argument("--quality-rules")
    parser.add_argument("--validation-artifact-dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = DataQualitySettings(
        source_contract_path=args.source_contract,
        aggregation_config_path=args.aggregation_config,
        split_config_path=args.split_config,
        patient_features_path=args.patient_features,
        split_manifest_path=args.split_manifest,
        split_dataset_dir=args.split_dataset_dir,
        source_evidence_path=args.source_evidence,
        quality_rules_path=args.quality_rules,
        validation_artifact_dir=args.validation_artifact_dir,
    )
    telemetry = create_telemetry(
        service_name="data-quality-pipeline",
        environment=settings.environment,
        policy=load_telemetry_policy(settings.telemetry_config_path),
        otlp_endpoint=str(settings.otlp_endpoint) if settings.otlp_endpoint else None,
    )
    failed = False
    result: DataPreparationResult
    try:
        with telemetry.run_scope(
            f"data_quality.{args.command}", attributes={"command": args.command}
        ):
            result = COMMANDS[args.command](settings)
            result_attributes = {
                name: value
                for name, value in asdict(result).items()
                if value is not None
            }
            if result.success is False:
                telemetry.event(
                    "data_quality.command.failed",
                    level=logging.ERROR,
                    attributes=result_attributes,
                )
                raise DataQualityValidationFailed(
                    "data quality validation did not pass"
                )
            telemetry.event(
                "data_quality.command.completed", attributes=result_attributes
            )
    except DataQualityValidationFailed:
        failed = True
    finally:
        telemetry.shutdown()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
