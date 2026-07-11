"""Generate derived datasets used by the Simple MLOps demo."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from aiqa_core.contracts import (
    DEFAULT_THRESHOLD,
    FEATURE_COLUMNS,
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    TARGET_COLUMN,
)
from aiqa_core.paths import data_path
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

SOURCE_DATASET = "human_vital_signs_dataset_2024.csv"
LABEL_MAP = {
    "High Risk": POSITIVE_LABEL,
    "Low Risk": NEGATIVE_LABEL,
    "high risk": POSITIVE_LABEL,
    "low risk": NEGATIVE_LABEL,
}
COLUMN_RENAME_MAP = {
    "Patient ID": "patient_id",
    "Heart Rate": "heart_rate",
    "Respiratory Rate": "respiratory_rate",
    "Timestamp": "timestamp",
    "Body Temperature": "body_temperature",
    "Oxygen Saturation": "oxygen_saturation",
    "Systolic Blood Pressure": "systolic_blood_pressure",
    "Diastolic Blood Pressure": "diastolic_blood_pressure",
    "Age": "age",
    "Gender": "gender",
    "Weight (kg)": "weight_kg",
    "Height (m)": "height_m",
    "Derived_HRV": "derived_hrv",
    "Derived_Pulse_Pressure": "derived_pulse_pressure",
    "Derived_BMI": "derived_bmi",
    "Derived_MAP": "derived_map",
    "Risk Category": TARGET_COLUMN,
}
VALID_RANGES = {
    "heart_rate": (1, 250),
    "respiratory_rate": (1, 80),
    "body_temperature": (30, 45),
    "oxygen_saturation": (0, 100),
    "systolic_blood_pressure": (50, 250),
    "diastolic_blood_pressure": (30, 150),
    "age": (0, 120),
    "weight_kg": (1, 300),
    "height_m": (0.5, 2.5),
}
SPLIT_RATIOS = {
    "evaluation_baseline": 0.10,
    "train": 0.55,
    "valid_baseline": 0.15,
    "test": 0.10,
    "holdout": 0.10,
}
OPERATIONAL_SAMPLE_SIZE = 120
STREAM_SAMPLE_SIZE = 2_000


def load_and_standardize_dataset(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe = dataframe.rename(columns=COLUMN_RENAME_MAP)
    if TARGET_COLUMN in dataframe.columns:
        dataframe[TARGET_COLUMN] = dataframe[TARGET_COLUMN].replace(LABEL_MAP)
    if "timestamp" in dataframe.columns:
        dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], errors="coerce")
    return dataframe


def filter_valid_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
    clean_dataframe = dataframe.copy()
    clean_dataframe = clean_dataframe[
        clean_dataframe[TARGET_COLUMN].isin({POSITIVE_LABEL, NEGATIVE_LABEL})
    ]

    for column, (minimum, maximum) in VALID_RANGES.items():
        if column not in clean_dataframe.columns:
            continue
        values = pd.to_numeric(clean_dataframe[column], errors="coerce")
        clean_dataframe = clean_dataframe[values.between(minimum, maximum)]

    clean_dataframe = clean_dataframe.dropna(
        subset=[*FEATURE_COLUMNS, TARGET_COLUMN]
    )
    return clean_dataframe.reset_index(drop=True)


def split_datasets(dataframe: pd.DataFrame) -> dict[str, pd.DataFrame]:
    shuffled = dataframe.sample(frac=1.0, random_state=42).reset_index(drop=True)
    row_count = len(shuffled)
    split_sizes = {
        name: int(row_count * ratio) for name, ratio in SPLIT_RATIOS.items()
    }
    split_sizes["train"] += row_count - sum(split_sizes.values())

    start = 0
    splits: dict[str, pd.DataFrame] = {}
    for name in SPLIT_RATIOS:
        end = start + split_sizes[name]
        splits[name] = shuffled.iloc[start:end].reset_index(drop=True)
        start = end
    return splits


def build_degraded_dataset(dataframe: pd.DataFrame) -> pd.DataFrame:
    degraded_dataframe = dataframe.copy()
    degraded_dataframe.loc[degraded_dataframe.index[::20], "heart_rate"] = pd.NA
    degraded_dataframe.loc[degraded_dataframe.index[::25], "oxygen_saturation"] = 135
    flip_index = degraded_dataframe.index[::30]
    degraded_dataframe.loc[flip_index, TARGET_COLUMN] = degraded_dataframe.loc[
        flip_index,
        TARGET_COLUMN,
    ].map({POSITIVE_LABEL: NEGATIVE_LABEL, NEGATIVE_LABEL: POSITIVE_LABEL})
    return degraded_dataframe


def build_serving_requests(
    dataframe: pd.DataFrame,
    sample_size: int = 50,
) -> pd.DataFrame:
    return dataframe.loc[:, list(FEATURE_COLUMNS)].head(sample_size).reset_index(
        drop=True
    )


def build_current_operational_requests(
    dataframe: pd.DataFrame,
    sample_size: int = OPERATIONAL_SAMPLE_SIZE,
) -> pd.DataFrame:
    if sample_size <= 0:
        return dataframe.head(0).copy()

    candidates = dataframe.copy().reset_index(drop=True)
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
    sample_size: int = 20,
) -> pd.DataFrame:
    invalid_dataframe = build_serving_requests(dataframe, sample_size)
    invalid_dataframe.loc[invalid_dataframe.index[::2], "heart_rate"] = pd.NA
    invalid_dataframe.loc[invalid_dataframe.index[1::2], "oxygen_saturation"] = 135
    return invalid_dataframe


def build_release_regression_cases(holdout: pd.DataFrame) -> pd.DataFrame:
    valid_rows = holdout.head(25).copy()
    valid_rows["case_type"] = "holdout_valid"
    valid_rows["expected_contract"] = "pass"

    drift_rows = build_current_operational_requests(holdout.iloc[25:], sample_size=25)
    drift_rows["case_type"] = "holdout_shifted"
    drift_rows["expected_contract"] = "pass"

    invalid_rows = build_invalid_serving_requests(holdout.iloc[50:], 20)
    invalid_rows[TARGET_COLUMN] = holdout.iloc[50:70][TARGET_COLUMN].to_list()
    invalid_rows["case_type"] = "invalid_input"
    invalid_rows["expected_contract"] = "fail"

    return pd.concat([valid_rows, drift_rows, invalid_rows], ignore_index=True)


def train_reference_classifier(dataframe: pd.DataFrame) -> Pipeline:
    labels = (dataframe[TARGET_COLUMN] == POSITIVE_LABEL).astype(int)
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=6,
                    min_samples_leaf=20,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ]
    )
    model.fit(dataframe.loc[:, list(FEATURE_COLUMNS)], labels)
    return model


def predict_positive_scores(
    model: Pipeline,
    dataframe: pd.DataFrame,
) -> list[float]:
    probabilities = model.predict_proba(dataframe.loc[:, list(FEATURE_COLUMNS)])
    return [float(value) for value in probabilities[:, 1]]


def build_operational_events(
    dataframe: pd.DataFrame,
    *,
    scenario: str,
    scores: Sequence[float],
    threshold: float = DEFAULT_THRESHOLD,
    max_events: int = OPERATIONAL_SAMPLE_SIZE,
) -> list[dict[str, str | float | int | bool | None]]:
    events: list[dict[str, str | float | int | bool | None]] = []
    rows = dataframe.head(max_events).reset_index(drop=True)
    event_scores = list(scores)
    if len(event_scores) < len(rows):
        msg = "scores must cover all operational event rows"
        raise ValueError(msg)

    for index, _row in rows.iterrows():
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


def write_jsonl(rows: list[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    return output_path


def prepare_datasets(
    source_path: Path | None = None,
    output_data_dir: Path | None = None,
) -> list[Path]:
    source = source_path or data_path(SOURCE_DATASET)
    output_dir = output_data_dir or data_path().resolve()
    if not source.exists():
        msg = f"Source dataset not found: {source}"
        raise FileNotFoundError(msg)

    base_dataframe = load_and_standardize_dataset(source)
    clean_dataframe = filter_valid_rows(base_dataframe)
    splits = split_datasets(clean_dataframe)
    model = train_reference_classifier(splits["train"])

    serving_requests_valid = build_serving_requests(
        splits["holdout"],
        sample_size=OPERATIONAL_SAMPLE_SIZE,
    )
    serving_requests_invalid = build_invalid_serving_requests(splits["holdout"])
    serving_requests_current = build_serving_requests(
        build_current_operational_requests(
            splits["holdout"],
            sample_size=OPERATIONAL_SAMPLE_SIZE,
        ),
        sample_size=OPERATIONAL_SAMPLE_SIZE,
    )
    serving_requests_current_stream = build_serving_requests(
        build_current_operational_requests(
            splits["holdout"],
            sample_size=STREAM_SAMPLE_SIZE,
        ),
        sample_size=STREAM_SAMPLE_SIZE,
    )
    operational_baseline = build_operational_events(
        serving_requests_valid,
        scenario="baseline",
        scores=predict_positive_scores(model, serving_requests_valid),
    )
    operational_current = build_operational_events(
        serving_requests_current,
        scenario="current",
        scores=predict_positive_scores(model, serving_requests_current),
    )
    operational_current_stream = build_operational_events(
        serving_requests_current_stream,
        scenario="current",
        scores=predict_positive_scores(model, serving_requests_current_stream),
        max_events=STREAM_SAMPLE_SIZE,
    )

    outputs = {
        "vital_signs.csv": base_dataframe,
        "vital_signs_standardized.csv": clean_dataframe,
        "vital_signs_evaluation_baseline.csv": splits["evaluation_baseline"],
        "vital_signs_train.csv": splits["train"],
        "vital_signs_valid_baseline.csv": splits["valid_baseline"],
        "vital_signs_valid_degraded.csv": build_degraded_dataset(
            splits["valid_baseline"]
        ),
        "vital_signs_test.csv": splits["test"],
        "vital_signs_operational_holdout.csv": splits["holdout"],
        "serving_requests.csv": serving_requests_valid.head(50),
        "drift_requests.csv": serving_requests_current.head(50),
        "serving_requests_valid.csv": serving_requests_valid,
        "serving_requests_current.csv": serving_requests_current,
        "serving_requests_current_stream.csv": serving_requests_current_stream,
        "serving_requests_invalid.csv": serving_requests_invalid,
        "release_regression_cases.csv": build_release_regression_cases(
            splits["holdout"]
        ),
    }

    written_paths: list[Path] = []
    for filename, dataframe in outputs.items():
        output_path = output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(output_path, index=False)
        written_paths.append(output_path)

    event_outputs = {
        "operational_baseline_events.jsonl": operational_baseline,
        "operational_current_events.jsonl": operational_current,
        "operational_current_stream_events.jsonl": operational_current_stream,
    }
    for filename, rows in event_outputs.items():
        written_paths.append(write_jsonl(rows, output_dir / filename))

    return written_paths
