"""Prepare derived datasets used by the course labs."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from ai_quality.common.config import load_yaml
from ai_quality.common.labels import NEGATIVE_LABEL, POSITIVE_LABEL
from ai_quality.common.paths import config_path, data_path
from ai_quality.data_quality.domain.dataset_schema import DatasetSchema
from ai_quality.data_quality.domain.quality_rule import DataQualityRules
from ai_quality.data_quality.infrastructure.pandas_dataset_reader import (
    load_and_standardize_dataset,
)
from ai_quality.model_quality.infrastructure.sklearn_classifier import (
    predict_positive_scores,
    train_sklearn_classifier,
)

SOURCE_DATASET = "human_vital_signs_dataset_2024.csv"
SPLIT_RATIOS = {
    "evaluation_baseline": 0.10,
    "train": 0.55,
    "valid_baseline": 0.15,
    "test": 0.10,
    "holdout": 0.10,
}
COURSE_DATA_OUTPUTS = (
    "vital_signs.csv",
    "vital_signs_standardized.csv",
    "vital_signs_evaluation_baseline.csv",
    "vital_signs_train.csv",
    "vital_signs_valid_baseline.csv",
    "vital_signs_valid_degraded.csv",
    "vital_signs_test.csv",
    "vital_signs_operational_holdout.csv",
    "serving_requests_valid.csv",
    "serving_requests_current.csv",
    "serving_requests_current_stream.csv",
    "serving_requests_invalid.csv",
    "release_regression_cases.csv",
)
COURSE_EVENT_OUTPUTS = (
    "operational_baseline_events.jsonl",
    "operational_current_events.jsonl",
    "operational_current_stream_events.jsonl",
)
OPERATIONAL_SAMPLE_SIZE = 120
STREAM_SAMPLE_SIZE = 2_000


def load_schema() -> DatasetSchema:
    """Load the course dataset schema."""
    return DatasetSchema.from_config(
        load_yaml(config_path("validation", "dataset_schema.yaml"))
    )


def load_rules() -> DataQualityRules:
    """Load the course data quality rules."""
    return DataQualityRules.from_config(
        load_yaml(config_path("validation", "data_quality_rules.yaml"))
    )


def filter_valid_rows(
    dataframe: pd.DataFrame,
    schema: DatasetSchema,
    rules: DataQualityRules,
) -> pd.DataFrame:
    """Return rows that satisfy basic label and range rules."""
    clean_dataframe = dataframe.copy()
    clean_dataframe = clean_dataframe[
        clean_dataframe[schema.target_column].isin(rules.allowed_labels)
    ]

    for valid_range in rules.valid_ranges:
        if valid_range.column not in clean_dataframe.columns:
            continue
        values = pd.to_numeric(clean_dataframe[valid_range.column], errors="coerce")
        clean_dataframe = clean_dataframe[
            values.between(valid_range.min_value, valid_range.max_value)
        ]

    clean_dataframe = clean_dataframe.dropna(
        subset=[*schema.model_feature_columns, schema.target_column]
    )
    return clean_dataframe.reset_index(drop=True)


def build_degraded_dataset(
    dataframe: pd.DataFrame,
    schema: DatasetSchema,
) -> pd.DataFrame:
    """Create a deterministic degraded validation dataset for chapter 2."""
    degraded_dataframe = dataframe.copy()

    if "heart_rate" in degraded_dataframe.columns:
        degraded_dataframe.loc[degraded_dataframe.index[::20], "heart_rate"] = pd.NA

    if "oxygen_saturation" in degraded_dataframe.columns:
        degraded_dataframe.loc[
            degraded_dataframe.index[::25],
            "oxygen_saturation",
        ] = 135

    if schema.target_column in degraded_dataframe.columns:
        flip_index = degraded_dataframe.index[::30]
        degraded_dataframe.loc[
            flip_index,
            schema.target_column,
        ] = degraded_dataframe.loc[
            flip_index,
            schema.target_column,
        ].map(
            {
                "high_risk": "low_risk",
                "low_risk": "high_risk",
            }
        )

    return degraded_dataframe


def split_course_datasets(dataframe: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split clean rows into the course dataset contract."""
    shuffled = dataframe.sample(frac=1.0, random_state=42).reset_index(drop=True)
    row_count = len(shuffled)
    split_sizes = {
        name: int(row_count * ratio) for name, ratio in SPLIT_RATIOS.items()
    }
    assigned = sum(split_sizes.values())
    split_sizes["train"] += row_count - assigned

    start = 0
    splits: dict[str, pd.DataFrame] = {}
    for name in SPLIT_RATIOS:
        end = start + split_sizes[name]
        splits[name] = shuffled.iloc[start:end].reset_index(drop=True)
        start = end
    return splits


def build_serving_requests(
    dataframe: pd.DataFrame,
    schema: DatasetSchema,
    sample_size: int = 50,
) -> pd.DataFrame:
    """Create example request payload rows for serving labs."""
    return dataframe.loc[:, list(schema.model_feature_columns)].head(
        sample_size
    ).reset_index(drop=True)


def build_current_operational_requests(
    dataframe: pd.DataFrame,
    sample_size: int = 120,
) -> pd.DataFrame:
    """Return real rows from a high-heart-rate, lower-oxygen holdout slice."""
    if sample_size <= 0:
        return dataframe.head(0).copy()

    candidates = dataframe.copy().reset_index(drop=True)
    if {"heart_rate", "oxygen_saturation"}.issubset(candidates.columns):
        heart_rate_cutoff = candidates["heart_rate"].quantile(0.55)
        oxygen_cutoff = candidates["oxygen_saturation"].quantile(0.45)
        candidates = candidates[
            (candidates["heart_rate"] >= heart_rate_cutoff)
            & (candidates["oxygen_saturation"] <= oxygen_cutoff)
        ]

    if len(candidates) >= sample_size:
        return candidates.sample(n=sample_size, random_state=42).reset_index(drop=True)

    return dataframe.head(sample_size).reset_index(drop=True)


def build_invalid_serving_requests(
    dataframe: pd.DataFrame,
    schema: DatasetSchema,
    sample_size: int = 20,
) -> pd.DataFrame:
    """Create invalid request rows from holdout-based serving examples."""
    invalid_dataframe = build_serving_requests(dataframe, schema, sample_size)

    if "heart_rate" in invalid_dataframe.columns:
        invalid_dataframe.loc[invalid_dataframe.index[::2], "heart_rate"] = pd.NA

    if "oxygen_saturation" in invalid_dataframe.columns:
        invalid_dataframe.loc[
            invalid_dataframe.index[1::2],
            "oxygen_saturation",
        ] = 135

    return invalid_dataframe


def build_release_regression_cases(
    holdout: pd.DataFrame,
    schema: DatasetSchema,
) -> pd.DataFrame:
    """Build release regression cases from holdout-derived rows."""
    valid_rows = holdout.head(25).copy()
    valid_rows["case_type"] = "holdout_valid"
    valid_rows["expected_contract"] = "pass"

    drift_rows = build_current_operational_requests(holdout.iloc[25:], sample_size=25)
    drift_rows["case_type"] = "holdout_shifted"
    drift_rows["expected_contract"] = "pass"

    invalid_rows = build_invalid_serving_requests(holdout.iloc[50:], schema, 20)
    invalid_rows[schema.target_column] = holdout.iloc[50:70][
        schema.target_column
    ].to_list()
    invalid_rows["case_type"] = "invalid_input"
    invalid_rows["expected_contract"] = "fail"

    return pd.concat([valid_rows, drift_rows, invalid_rows], ignore_index=True)


def build_operational_events(
    dataframe: pd.DataFrame,
    *,
    scenario: str,
    threshold: float = 0.5,
    scores: Sequence[float],
    max_events: int = OPERATIONAL_SAMPLE_SIZE,
) -> list[dict[str, str | float | int | bool | None]]:
    """Build holdout-derived operational events for observability labs."""
    events: list[dict[str, str | float | int | bool | None]] = []
    rows = dataframe.head(max_events).reset_index(drop=True)
    event_scores = list(scores)
    if len(event_scores) < len(rows):
        msg = "scores must cover all operational event rows"
        raise ValueError(msg)

    for index, _ in enumerate(rows.iterrows()):
        validation_failure = scenario == "current" and index % 17 == 0
        score = round(float(event_scores[index]), 4)
        prediction = POSITIVE_LABEL if score >= threshold else NEGATIVE_LABEL
        failed_field = None
        error_detail = None
        if validation_failure:
            failed_field = "oxygen_saturation" if index % 2 == 0 else "heart_rate"
            error_detail = (
                "oxygen_saturation is outside accepted serving range"
                if failed_field == "oxygen_saturation"
                else "heart_rate is missing from client payload"
            )

        events.append(
            {
                "timestamp": (
                    f"2026-01-01T09:{index // 12:02d}:"
                    f"{(index % 12) * 5:02d}+00:00"
                ),
                "request_id": f"{scenario}-{index:04d}",
                "trace_id": f"{scenario}-trace-{index // 3:04d}",
                "model_version": "v1",
                "score": score,
                "threshold": threshold,
                "prediction": prediction,
                "latency_ms": 180.0 + (index % 8) * 12.5
                if scenario == "current"
                else 60.0 + (index % 8) * 12.5,
                "status_code": 422 if validation_failure else 200,
                "validation_failure": validation_failure,
                "client_id": "partner-feed-v2"
                if validation_failure
                else (
                    "mobile-checkin-v2"
                    if scenario == "current"
                    else "baseline-client-v1"
                ),
                "source_system": "upstream-partner-feed"
                if validation_failure
                else (
                    "mobile-checkin"
                    if scenario == "current"
                    else "holdout-baseline"
                ),
                "failed_field": failed_field,
                "error_category": "schema_validation" if validation_failure else None,
                "error_detail": error_detail,
                "owner": "Client Integration" if validation_failure else None,
            }
        )
    return events


def write_jsonl(
    rows: list[dict[str, str | float | int | bool | None]],
    output_path: Path,
) -> Path:
    """Write dictionaries to a JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    return output_path


def prepare_datasets(source_path: Path | None = None) -> list[Path]:
    """Prepare all derived CSV files used by the course."""
    schema = load_schema()
    rules = load_rules()
    source = source_path or data_path(SOURCE_DATASET)

    if not source.exists():
        msg = f"Source dataset not found: {source}"
        raise FileNotFoundError(msg)

    base_dataframe = load_and_standardize_dataset(source, schema)
    clean_dataframe = filter_valid_rows(base_dataframe, schema, rules)
    splits = split_course_datasets(clean_dataframe)
    feature_columns = list(schema.model_feature_columns)
    model = train_sklearn_classifier(
        dataframe=splits["train"],
        feature_columns=feature_columns,
        target_column=schema.target_column,
    )

    serving_requests_valid = build_serving_requests(
        splits["holdout"],
        schema,
        sample_size=OPERATIONAL_SAMPLE_SIZE,
    )
    serving_requests_invalid = build_invalid_serving_requests(splits["holdout"], schema)
    serving_requests_current = build_serving_requests(
        build_current_operational_requests(
            splits["holdout"],
            sample_size=OPERATIONAL_SAMPLE_SIZE,
        ),
        schema,
        sample_size=OPERATIONAL_SAMPLE_SIZE,
    )
    serving_requests_current_stream = build_serving_requests(
        build_current_operational_requests(
            splits["holdout"],
            sample_size=STREAM_SAMPLE_SIZE,
        ),
        schema,
        sample_size=STREAM_SAMPLE_SIZE,
    )
    operational_baseline = build_operational_events(
        serving_requests_valid,
        scenario="baseline",
        scores=predict_positive_scores(model, serving_requests_valid, feature_columns),
    )
    operational_current = build_operational_events(
        serving_requests_current,
        scenario="current",
        scores=predict_positive_scores(
            model,
            serving_requests_current,
            feature_columns,
        ),
    )
    operational_current_stream = build_operational_events(
        serving_requests_current_stream,
        scenario="current",
        scores=predict_positive_scores(
            model,
            serving_requests_current_stream,
            feature_columns,
        ),
        max_events=STREAM_SAMPLE_SIZE,
    )

    outputs = {
        "vital_signs.csv": base_dataframe,
        "vital_signs_standardized.csv": clean_dataframe,
        "vital_signs_evaluation_baseline.csv": splits["evaluation_baseline"],
        "vital_signs_train.csv": splits["train"],
        "vital_signs_valid_baseline.csv": splits["valid_baseline"],
        "vital_signs_valid_degraded.csv": build_degraded_dataset(
            splits["valid_baseline"],
            schema,
        ),
        "vital_signs_test.csv": splits["test"],
        "vital_signs_operational_holdout.csv": splits["holdout"],
        "serving_requests_valid.csv": serving_requests_valid,
        "serving_requests_current.csv": serving_requests_current,
        "serving_requests_current_stream.csv": serving_requests_current_stream,
        "serving_requests_invalid.csv": serving_requests_invalid,
        "release_regression_cases.csv": build_release_regression_cases(
            splits["holdout"],
            schema,
        ),
    }

    written_paths: list[Path] = []
    for filename, dataframe in outputs.items():
        output_path = data_path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(output_path, index=False)
        written_paths.append(output_path)

    event_outputs = {
        "operational_baseline_events.jsonl": operational_baseline,
        "operational_current_events.jsonl": operational_current,
        "operational_current_stream_events.jsonl": operational_current_stream,
    }
    for filename, rows in event_outputs.items():
        written_paths.append(write_jsonl(rows, data_path(filename)))

    return written_paths
