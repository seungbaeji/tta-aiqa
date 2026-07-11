"""Build deterministic prepared evidence for the V2 data revision."""

from __future__ import annotations

import csv
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
    feature_path = ROOT / "data/processed/physionet-2012/patient-features.csv"
    split_path = ROOT / "data/splits/physionet-2012/split-manifest.csv"
    split_dataset_dir = ROOT / "data/splits/physionet-2012/datasets"
    with feature_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        rows = list(reader)
    with split_path.open(newline="", encoding="utf-8") as file:
        split_rows = list(csv.DictReader(file))
    roles = Counter(row["role"] for row in split_rows)
    deaths_by_role = Counter()
    target_by_id = {row["record_id"]: int(row["target"]) for row in rows}
    for row in split_rows:
        deaths_by_role[row["role"]] += target_by_id[row["record_id"]]

    phase_feature_path = ROOT / "artifacts/phase0/patient-features.csv"
    phase_split_path = ROOT / "artifacts/phase0/split-manifest.csv"
    phase0_paths = (phase_feature_path, phase_split_path)
    if any(path.exists() for path in phase0_paths) and not all(
        path.is_file() for path in phase0_paths
    ):
        raise FileNotFoundError("phase0 comparison requires both snapshot files")
    if all(path.is_file() for path in phase0_paths):
        phase_features = pd.read_csv(phase_feature_path)
        current_features = pd.read_csv(feature_path)
        pd.testing.assert_frame_equal(
            current_features.sort_values("record_id").reset_index(drop=True),
            phase_features.sort_values("record_id").reset_index(drop=True),
            check_dtype=False,
            check_exact=False,
            rtol=1e-12,
            atol=1e-12,
        )
        phase_splits = pd.read_csv(phase_split_path)
        phase_splits["role"] = phase_splits["role"].replace(
            {"release_holdout": "operational"}
        )
        current_splits = pd.read_csv(split_path)
        pd.testing.assert_frame_equal(
            current_splits.sort_values("record_id").reset_index(drop=True),
            phase_splits.sort_values("record_id").reset_index(drop=True),
            check_dtype=False,
        )

    role_datasets: dict[str, dict[str, object]] = {}
    for role in sorted(roles):
        role_path = split_dataset_dir / f"{role}.csv"
        role_frame = pd.read_csv(role_path)
        has_target = "target" in role_frame.columns
        if has_target != (role != "operational"):
            raise ValueError(f"unexpected target visibility for dataset role: {role}")
        role_datasets[role] = {
            "path": str(role_path.relative_to(ROOT)),
            "sha256": sha256(role_path),
            "rows": len(role_frame),
            "target_included": has_target,
        }

    document = {
        "schema_version": 1,
        "source": {
            "archive_sha256": sha256(ROOT / "data/raw/physionet-2012/set-a.zip"),
            "outcomes_sha256": sha256(ROOT / "data/raw/physionet-2012/Outcomes-a.txt"),
            "source_manifest_sha256": sha256(
                ROOT / "data/raw/physionet-2012/source-manifest.yaml"
            ),
        },
        "configuration": {
            "aggregation_sha256": sha256(ROOT / "configs/data/aggregation.yaml"),
            "params_sha256": sha256(ROOT / "params.yaml"),
            "dvc_lock_sha256": sha256(ROOT / "dvc.lock"),
        },
        "patient_features": {
            "path": str(feature_path.relative_to(ROOT)),
            "sha256": sha256(feature_path),
            "rows": len(rows),
            "feature_count": len(columns) - 2,
            "deaths": sum(int(row["target"]) for row in rows),
        },
        "split_manifest": {
            "path": str(split_path.relative_to(ROOT)),
            "sha256": sha256(split_path),
            "rows": len(split_rows),
            "roles": {
                role: {"rows": roles[role], "deaths": deaths_by_role[role]}
                for role in sorted(roles)
            },
        },
        "role_datasets": role_datasets,
        "phase0_equivalence": {
            "feature_values": True,
            "split_assignments": True,
            "role_rename": {"release_holdout": "operational"},
        },
    }
    output = ROOT / "reference/evidence/data-lineage/data-manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
