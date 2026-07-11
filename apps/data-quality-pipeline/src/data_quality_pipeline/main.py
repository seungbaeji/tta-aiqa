"""CLI entry point for data preparation and validation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict

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
    result = COMMANDS[args.command](settings)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    if result.success is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
