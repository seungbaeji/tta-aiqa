"""Run one DVC data stage with repository-default paths."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from data_quality_pipeline.bootstrap import (
    DataPreparationResult,
    aggregate,
    extract_source,
    revise_split,
    split,
    verify_source,
)
from data_quality_pipeline.settings import DataQualitySettings

ROOT = Path(__file__).resolve().parents[1]
COMMANDS: dict[str, Callable[[DataQualitySettings], DataPreparationResult]] = {
    "verify-source": verify_source,
    "extract": extract_source,
    "aggregate": aggregate,
    "split": split,
    "revise-split": revise_split,
}


def repository_settings() -> DataQualitySettings:
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=tuple(COMMANDS))
    args = parser.parse_args()
    result = COMMANDS[args.command](repository_settings())
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
