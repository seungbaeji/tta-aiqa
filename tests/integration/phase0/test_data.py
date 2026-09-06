from pathlib import Path

import pandas as pd

from scripts.phase0.config import load_config
from scripts.phase0.data import (
    create_split_manifest,
    load_outcomes,
    parse_patient_record,
)

CONFIG_PATH = Path("configs/phase0/physionet-2012.yaml")


def test_parse_patient_record_aggregates_without_record_id_feature() -> None:
    config = load_config(CONFIG_PATH)

    features, evidence = parse_patient_record(
        config.source.records_dir / "132539.txt", config
    )

    assert features["record_id"] == 132539
    assert "heart_rate__mean" in features
    assert "RecordID" not in features
    assert evidence["record_id"] == 132539


def test_outcomes_loader_exposes_only_id_and_target() -> None:
    config = load_config(CONFIG_PATH)

    outcomes = load_outcomes(config)

    assert list(outcomes.columns) == ["record_id", "target"]
    assert set(config.source.blocked_outcome_columns).isdisjoint(outcomes.columns)


def test_split_manifest_is_patient_disjoint_and_exact() -> None:
    config = load_config(CONFIG_PATH)
    rows = pd.DataFrame(
        {
            "record_id": range(1000),
            "target": [0] * 860 + [1] * 140,
        }
    )

    manifest = create_split_manifest(rows, config)

    assert manifest["record_id"].is_unique
    assert manifest["role"].value_counts().to_dict() == {
        "train": 600,
        "valid": 150,
        "test": 150,
        "release_holdout": 100,
    }
