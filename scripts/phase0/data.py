"""PhysioNet parsing, aggregation, and deterministic split construction."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from scripts.phase0.config import Phase0Config

EXPECTED_RECORD_HEADER = ["Time", "Parameter", "Value"]
OUTCOME_ID = "RecordID"


@dataclass(frozen=True)
class PreparedData:
    """Prepared patient features plus auditable source evidence."""

    features: pd.DataFrame
    splits: pd.DataFrame
    profile: dict[str, Any]


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_time(value: str) -> int:
    hours, minutes = (int(part) for part in value.split(":"))
    if hours < 0 or not 0 <= minutes < 60:
        raise ValueError(f"invalid PhysioNet time: {value}")
    return hours * 60 + minutes


def _aggregate(values: list[tuple[int, float]], statistic: str) -> float:
    ordered = sorted(values)
    numbers = np.asarray([value for _, value in ordered], dtype=float)
    if statistic == "min":
        return float(numbers.min())
    if statistic == "max":
        return float(numbers.max())
    if statistic == "mean":
        return float(numbers.mean())
    if statistic == "last":
        return float(ordered[-1][1])
    if statistic == "count":
        return float(len(numbers))
    if statistic == "sum":
        return float(numbers.sum())
    raise ValueError(f"unsupported aggregation statistic: {statistic}")


def parse_patient_record(
    path: Path, config: Phase0Config
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse one patient record into configured aggregate features."""
    static_sources = config.aggregation.static_parameters
    series_sources = config.aggregation.series_parameters
    selected = set(static_sources) | set(series_sources) | {OUTCOME_ID}
    missing_sentinel = config.aggregation.missing_sentinel

    static_values: dict[str, float] = {}
    series_values: dict[str, list[tuple[int, float]]] = {
        parameter: [] for parameter in series_sources
    }
    source_parameters: set[str] = set()
    record_id: int | None = None
    row_count = 0
    sentinel_count = 0

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != EXPECTED_RECORD_HEADER:
            raise ValueError(f"unexpected header in {path}: {reader.fieldnames}")
        for row in reader:
            row_count += 1
            minute = _parse_time(row["Time"])
            parameter = row["Parameter"]
            source_parameters.add(parameter)
            value = float(row["Value"])

            if parameter == OUTCOME_ID:
                record_id = int(value)
                continue
            if parameter not in selected:
                continue
            if value == missing_sentinel:
                sentinel_count += 1
                continue
            if parameter in static_sources:
                static_values.setdefault(parameter, value)
            elif parameter in series_sources:
                series_values[parameter].append((minute, value))

    if record_id is None:
        raise ValueError(f"RecordID is missing from {path}")
    if path.stem != str(record_id):
        raise ValueError(f"filename/RecordID mismatch in {path}: {record_id}")

    features: dict[str, Any] = {"record_id": record_id}
    for parameter, output_name in static_sources.items():
        features[output_name] = static_values.get(parameter, np.nan)
        features[f"{output_name}__missing"] = float(parameter not in static_values)
    for parameter, aggregation in series_sources.items():
        values = series_values[parameter]
        for statistic in aggregation.statistics:
            name = f"{aggregation.output_name}__{statistic}"
            features[name] = _aggregate(values, statistic) if values else np.nan
        features[f"{aggregation.output_name}__missing"] = float(not values)

    evidence = {
        "record_id": record_id,
        "row_count": row_count,
        "sentinel_count": sentinel_count,
        "parameters": sorted(source_parameters),
        "selected_parameter_counts": {
            parameter: len(values) for parameter, values in series_values.items()
        },
    }
    return features, evidence


def load_outcomes(config: Phase0Config) -> pd.DataFrame:
    """Load only the identifier and target from the outcome-side file."""
    outcomes = pd.read_csv(config.source.outcomes_path)
    required = {
        OUTCOME_ID,
        config.source.target_column,
        *config.source.blocked_outcome_columns,
    }
    missing = required - set(outcomes.columns)
    if missing:
        raise ValueError(f"outcome columns missing: {sorted(missing)}")
    if outcomes[OUTCOME_ID].duplicated().any():
        raise ValueError("duplicate RecordID values in outcomes")
    target_values = set(outcomes[config.source.target_column].unique())
    if target_values != {0, 1}:
        raise ValueError(f"unexpected target values: {sorted(target_values)}")
    return outcomes[[OUTCOME_ID, config.source.target_column]].rename(
        columns={OUTCOME_ID: "record_id", config.source.target_column: "target"}
    )


def create_split_manifest(features: pd.DataFrame, config: Phase0Config) -> pd.DataFrame:
    """Create exact patient-level stratified train/valid/test/holdout roles."""
    ids = features["record_id"]
    target = features["target"]
    split = config.split

    development_ids, holdout_ids = train_test_split(
        ids,
        test_size=split.release_holdout_ratio,
        random_state=split.random_seed,
        stratify=target,
    )
    development = features.set_index("record_id").loc[development_ids]
    test_fraction = split.test_ratio / (
        split.train_ratio + split.valid_ratio + split.test_ratio
    )
    train_valid_ids, test_ids = train_test_split(
        development.index,
        test_size=test_fraction,
        random_state=split.random_seed,
        stratify=development["target"],
    )
    train_valid = features.set_index("record_id").loc[train_valid_ids]
    valid_fraction = split.valid_ratio / (split.train_ratio + split.valid_ratio)
    train_ids, valid_ids = train_test_split(
        train_valid.index,
        test_size=valid_fraction,
        random_state=split.random_seed,
        stratify=train_valid["target"],
    )

    roles = {
        **{int(record_id): "train" for record_id in train_ids},
        **{int(record_id): "valid" for record_id in valid_ids},
        **{int(record_id): "test" for record_id in test_ids},
        **{int(record_id): "release_holdout" for record_id in holdout_ids},
    }
    manifest = pd.DataFrame(
        {"record_id": features["record_id"], "role": features["record_id"].map(roles)}
    ).sort_values("record_id", ignore_index=True)
    if manifest["role"].isna().any() or manifest["record_id"].duplicated().any():
        raise ValueError("split manifest is incomplete or contains duplicate patients")
    return manifest


def prepare_data(config: Phase0Config) -> PreparedData:
    """Validate sources and construct the patient-level feasibility dataset."""
    archive_hash = sha256_file(config.source.archive_path)
    outcomes_hash = sha256_file(config.source.outcomes_path)
    if archive_hash != config.source.archive_sha256:
        raise ValueError(f"set-a archive checksum mismatch: {archive_hash}")
    if outcomes_hash != config.source.outcomes_sha256:
        raise ValueError(f"outcomes checksum mismatch: {outcomes_hash}")

    paths = sorted(config.source.records_dir.glob("*.txt"))
    if len(paths) != config.source.expected_record_count:
        raise ValueError(
            f"expected {config.source.expected_record_count} records, got {len(paths)}"
        )

    feature_rows: list[dict[str, Any]] = []
    parameter_coverage: Counter[str] = Counter()
    total_measurement_rows = 0
    total_sentinels = 0
    for path in paths:
        features, evidence = parse_patient_record(path, config)
        feature_rows.append(features)
        total_measurement_rows += int(evidence["row_count"])
        total_sentinels += int(evidence["sentinel_count"])
        parameter_coverage.update(evidence["parameters"])

    patient_features = pd.DataFrame(feature_rows)
    if patient_features["record_id"].duplicated().any():
        raise ValueError("duplicate RecordID values in patient records")
    outcomes = load_outcomes(config)
    merged = patient_features.merge(
        outcomes, on="record_id", how="outer", indicator=True
    )
    join_failures = int((merged["_merge"] != "both").sum())
    if join_failures:
        raise ValueError(f"patient/outcome join failures: {join_failures}")
    merged = merged.drop(columns="_merge").sort_values("record_id", ignore_index=True)

    death_count = int(merged["target"].sum())
    if death_count != config.source.expected_death_count:
        raise ValueError(
            f"expected {config.source.expected_death_count} deaths, got {death_count}"
        )
    splits = create_split_manifest(merged, config)
    role_summary = (
        merged[["record_id", "target"]]
        .merge(splits, on="record_id")
        .groupby("role", sort=True)["target"]
        .agg(rows="count", deaths="sum")
    )
    role_summary["death_rate"] = role_summary["deaths"] / role_summary["rows"]

    blocked_in_features = set(config.source.blocked_outcome_columns) & set(
        merged.columns
    )
    profile = {
        "schema_version": 1,
        "source": {
            "archive_sha256": archive_hash,
            "outcomes_sha256": outcomes_hash,
            "record_count": len(paths),
            "outcome_count": len(outcomes),
            "join_failures": join_failures,
            "measurement_rows": total_measurement_rows,
            "missing_sentinel_count_in_selected_parameters": total_sentinels,
        },
        "target": {
            "deaths": death_count,
            "survivors": int(len(merged) - death_count),
            "death_rate": death_count / len(merged),
        },
        "features": {
            "count": len(merged.columns) - 2,
            "blocked_outcome_columns_present": sorted(blocked_in_features),
            "parameter_record_coverage": {
                parameter: count / len(paths)
                for parameter, count in sorted(parameter_coverage.items())
            },
        },
        "splits": role_summary.reset_index().to_dict(orient="records"),
        "gates": {
            "record_count_matches": len(paths) == config.source.expected_record_count,
            "outcome_count_matches": len(outcomes)
            == config.source.expected_record_count,
            "join_complete": join_failures == 0,
            "target_support_matches": death_count == config.source.expected_death_count,
            "blocked_outcomes_absent": not blocked_in_features,
        },
    }
    profile["f0_passed"] = all(profile["gates"].values())
    return PreparedData(features=merged, splits=splits, profile=profile)
