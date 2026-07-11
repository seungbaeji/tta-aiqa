"""Build prepared lineage evidence for the approved V2 split revision."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parent_path = ROOT / "data/splits/physionet-2012/split-manifest.csv"
    revision_root = ROOT / "data/splits/physionet-2012/revisions/v2"
    revision_path = revision_root / "split-manifest.csv"
    feature_path = ROOT / "data/processed/physionet-2012/patient-features.csv"
    parent = pd.read_csv(parent_path).set_index("record_id")
    revision = pd.read_csv(revision_path).set_index("record_id")
    features = pd.read_csv(feature_path).set_index("record_id")
    if set(parent.index) != set(revision.index) or set(revision.index) != set(
        features.index
    ):
        raise ValueError("split revision does not cover the same patient cohort")

    transitions = Counter(
        (parent.loc[record_id, "role"], revision.loc[record_id, "role"])
        for record_id in revision.index
    )
    expected_transitions = {
        ("train", "train"): 2400,
        ("valid", "valid"): 600,
        ("test", "train"): 500,
        ("test", "operational"): 100,
        ("operational", "test"): 400,
    }
    if dict(transitions) != expected_transitions:
        raise ValueError(f"unexpected split revision ancestry: {dict(transitions)}")

    role_datasets: dict[str, dict[str, object]] = {}
    for role in ("train", "valid", "test", "operational"):
        path = revision_root / "datasets" / f"{role}.csv"
        frame = pd.read_csv(path)
        ids = revision.index[revision["role"] == role]
        expected_target = role != "operational"
        if ("target" in frame.columns) is not expected_target:
            raise ValueError(f"unexpected target visibility for V2 role: {role}")
        if set(frame["record_id"]) != set(ids):
            raise ValueError(f"V2 role dataset does not match its manifest: {role}")
        role_datasets[role] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "rows": len(frame),
            "deaths": int(features.loc[ids, "target"].sum()),
            "target_included": expected_target,
        }

    parent_evidence = json.loads(
        (ROOT / "reference/evidence/data-lineage/data-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    document = {
        "schema_version": 1,
        "revision": "v2",
        "parent_revision": "v1",
        "approval": "scenario_review_option_2",
        "source": parent_evidence["source"],
        "configuration": {
            "split_seed": 43,
            "split_revision_sha256": sha256(
                ROOT / "configs/data/split-revisions/v2.yaml"
            ),
            "dvc_lock_sha256": sha256(ROOT / "dvc.lock"),
            "parent_manifest_sha256": sha256(parent_path),
            "revision_manifest_sha256": sha256(revision_path),
        },
        "role_datasets": role_datasets,
        "ancestry": {
            f"{source}_to_{target}": count
            for (source, target), count in sorted(transitions.items())
        },
        "invariants": {
            "parent_operational_is_new_sealed_test": True,
            "parent_test_is_not_new_test": True,
            "parent_train_and_valid_are_stable": True,
            "operational_target_removed": True,
            "roles_are_disjoint_and_exhaustive": True,
        },
    }
    output = ROOT / "reference/evidence/data-lineage/split-revision-v2.json"
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
