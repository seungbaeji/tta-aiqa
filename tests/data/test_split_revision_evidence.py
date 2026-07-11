"""Prepared V2 split revision lineage evidence tests."""

import json
from pathlib import Path


def test_v2_split_evidence_preserves_unseen_test_ancestry() -> None:
    evidence = json.loads(
        Path("reference/evidence/data-lineage/split-revision-v2.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["revision"] == "v2"
    assert evidence["parent_revision"] == "v1"
    assert evidence["ancestry"] == {
        "operational_to_test": 400,
        "test_to_operational": 100,
        "test_to_train": 500,
        "train_to_train": 2400,
        "valid_to_valid": 600,
    }
    assert {role: item["rows"] for role, item in evidence["role_datasets"].items()} == {
        "operational": 100,
        "test": 400,
        "train": 2900,
        "valid": 600,
    }
    assert evidence["role_datasets"]["operational"]["target_included"] is False
    assert all(evidence["invariants"].values())
