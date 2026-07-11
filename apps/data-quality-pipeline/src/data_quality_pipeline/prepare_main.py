"""DVC-facing CLI with no Great Expectations dependency in its code path."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict

from data_quality_pipeline.bootstrap import (
    DataPreparationResult,
    aggregate,
    extract_source,
    revise_split,
    split,
    verify_source,
)
from data_quality_pipeline.settings import DataQualitySettings

COMMANDS: dict[str, Callable[[DataQualitySettings], DataPreparationResult]] = {
    "verify-source": verify_source,
    "extract": extract_source,
    "aggregate": aggregate,
    "split": split,
    "revise-split": revise_split,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=tuple(COMMANDS))
    parser.add_argument("--source-contract", required=True)
    parser.add_argument("--aggregation-config", required=True)
    parser.add_argument("--split-config", required=True)
    parser.add_argument("--patient-features", required=True)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--split-dataset-dir", required=True)
    parser.add_argument("--source-evidence", required=True)
    parser.add_argument("--split-revision-config")
    parser.add_argument("--revision-split-manifest")
    parser.add_argument("--revision-split-dataset-dir")
    args = parser.parse_args()
    settings = DataQualitySettings(
        source_contract_path=args.source_contract,
        aggregation_config_path=args.aggregation_config,
        split_config_path=args.split_config,
        patient_features_path=args.patient_features,
        split_manifest_path=args.split_manifest,
        split_dataset_dir=args.split_dataset_dir,
        source_evidence_path=args.source_evidence,
        split_revision_config_path=args.split_revision_config,
        revision_split_manifest_path=args.revision_split_manifest,
        revision_split_dataset_dir=args.revision_split_dataset_dir,
    )
    result = COMMANDS[args.command](settings)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
