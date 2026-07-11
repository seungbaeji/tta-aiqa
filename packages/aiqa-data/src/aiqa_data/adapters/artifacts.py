"""Deterministic CSV artifact writer."""

import csv
import json
from pathlib import Path

from aiqa_data.application import PreparedPatientFeatures, PreparedSplitManifest
from aiqa_data.domain import DatasetRole, PatientFeatureRow, SplitAssignment


def write_dataset_csv(dataset: PreparedPatientFeatures, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["record_id", *dataset.feature_names, "target"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(row.as_mapping() for row in dataset.rows)


def write_split_csv(dataset: PreparedSplitManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["record_id", "role"])
        writer.writeheader()
        writer.writerows(
            {"record_id": item.record_id, "role": item.role.value}
            for item in dataset.splits
        )


def read_dataset_csv(path: Path) -> PreparedPatientFeatures:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        if len(fieldnames) < 3 or fieldnames[0] != "record_id":
            raise ValueError("invalid patient feature CSV header")
        if fieldnames[-1] != "target":
            raise ValueError("patient feature CSV target must be the final column")
        feature_names = tuple(fieldnames[1:-1])
        rows = tuple(
            PatientFeatureRow(
                record_id=int(row["record_id"]),
                target=int(row["target"]),
                values=tuple(
                    (name, float(row[name]) if row[name] != "" else None)
                    for name in feature_names
                ),
            )
            for row in reader
        )
    return PreparedPatientFeatures(feature_names=feature_names, rows=rows)


def read_split_csv(path: Path) -> PreparedSplitManifest:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["record_id", "role"]:
            raise ValueError("invalid split manifest CSV header")
        splits = tuple(
            SplitAssignment(
                record_id=int(row["record_id"]),
                role=DatasetRole(row["role"]),
            )
            for row in reader
        )
    return PreparedSplitManifest(splits=splits)


def write_json(document: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_role_datasets(
    features: PreparedPatientFeatures,
    manifest: PreparedSplitManifest,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = {row.record_id: row for row in features.rows}
    assignments: dict[str, list[int]] = {}
    for item in manifest.splits:
        assignments.setdefault(item.role.value, []).append(item.record_id)
    for role, record_ids in sorted(assignments.items()):
        include_target = role != "operational"
        columns = ["record_id", *features.feature_names]
        if include_target:
            columns.append("target")
        with (output_dir / f"{role}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for record_id in sorted(record_ids):
                row = rows[record_id].as_mapping()
                if not include_target:
                    row.pop("target")
                writer.writerow(row)
