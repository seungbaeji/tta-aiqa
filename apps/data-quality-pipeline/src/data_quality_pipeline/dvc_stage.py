"""Run one repository-default data preparation stage for DVC."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from aiqa_observability import create_telemetry, load_telemetry_policy

from data_quality_pipeline.bootstrap import (
    DataPreparationResult,
    aggregate,
    extract_source,
    revise_split,
    split,
    verify_source,
)
from data_quality_pipeline.settings import DataQualitySettings

ROOT = Path(__file__).resolve().parents[4]
COMMANDS: dict[str, Callable[[DataQualitySettings], DataPreparationResult]] = {
    "verify-source": verify_source,
    "extract": extract_source,
    "aggregate": aggregate,
    "split": split,
    "revise-split": revise_split,
}


def repository_settings() -> DataQualitySettings:
    """Build stage settings from the repository's canonical paths."""
    return DataQualitySettings(
        source_contract_path=ROOT / "configs/contracts/physionet-record.yaml",
        aggregation_config_path=ROOT / "configs/data/aggregation.yaml",
        split_config_path=ROOT / "params.yaml",
        patient_features_path=(
            ROOT / "data/processed/physionet-2012/patient-features.csv"
        ),
        split_manifest_path=ROOT / "data/splits/physionet-2012/split-manifest.csv",
        split_dataset_dir=ROOT / "data/splits/physionet-2012/datasets",
        source_evidence_path=ROOT / "artifacts/data-quality/source-integrity.json",
        split_revision_config_path=ROOT / "configs/data/split-revisions/v2.yaml",
        revision_split_manifest_path=(
            ROOT / "data/splits/physionet-2012/revisions/v2/split-manifest.csv"
        ),
        revision_split_dataset_dir=(
            ROOT / "data/splits/physionet-2012/revisions/v2/datasets"
        ),
    )


def main() -> None:
    """Execute the selected DVC data stage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=tuple(COMMANDS))
    args = parser.parse_args()
    settings = repository_settings()
    telemetry = create_telemetry(
        service_name="data-quality-pipeline",
        environment=settings.environment,
        policy=load_telemetry_policy(settings.telemetry_config_path),
        otlp_endpoint=str(settings.otlp_endpoint) if settings.otlp_endpoint else None,
    )
    try:
        with telemetry.run_scope(
            f"data_quality.{args.command}", attributes={"command": args.command}
        ):
            result = COMMANDS[args.command](settings)
            telemetry.event(
                "data_quality.command.completed",
                attributes={
                    name: value
                    for name, value in asdict(result).items()
                    if value is not None
                },
            )
    finally:
        telemetry.shutdown()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
