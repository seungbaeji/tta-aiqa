"""Run one repository-default data preparation stage for DVC."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from data_quality_pipeline.bootstrap import bootstrap
from data_quality_pipeline.domain import DataQualityStage
from data_quality_pipeline.settings import DataQualitySettings

ROOT = Path(__file__).resolve().parents[4]
DVC_STAGES = (
    DataQualityStage.VERIFY_SOURCE,
    DataQualityStage.EXTRACT,
    DataQualityStage.AGGREGATE,
    DataQualityStage.SPLIT,
    DataQualityStage.REVISE_SPLIT,
)


class DvcStageDto(BaseModel):
    """Validated external DVC stage command."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: DataQualityStage


def repository_settings() -> DataQualitySettings:
    """Build Pydantic runtime settings from the repository's canonical paths."""
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


def parse_args() -> DvcStageDto:
    """Parse and validate a DVC-selected stage name."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=tuple(stage.value for stage in DVC_STAGES))
    return DvcStageDto.model_validate(vars(parser.parse_args()))


def main() -> None:
    """Execute the selected DVC stage through the shared runtime operation."""
    command = parse_args()
    runtime = bootstrap(repository_settings())
    try:
        with runtime.telemetry.run_scope(
            f"data_quality.{command.stage}",
            attributes={"command": command.stage},
        ):
            result = runtime.run(command.stage)
            runtime.telemetry.event(
                "data_quality.command.completed",
                attributes={
                    name: value
                    for name, value in asdict(result).items()
                    if value is not None
                },
            )
    finally:
        runtime.telemetry.shutdown()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
