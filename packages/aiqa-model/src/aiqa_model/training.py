"""Training and MLflow logging for the Simple MLOps demo."""

from __future__ import annotations

import inspect
import json
import time
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import joblib
import pandas as pd
from aiqa_core.contracts import (
    DEFAULT_THRESHOLD,
    FEATURE_COLUMNS,
    POSITIVE_LABEL,
    TARGET_COLUMN,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class TrainConfig:
    train_path: str
    test_path: str
    model_path: str
    metadata_path: str
    tracking_uri: str
    experiment: str
    train_sample_size: int
    test_sample_size: int
    n_estimators: int


def wait_for_mlflow(tracking_uri: str, timeout_seconds: float = 60.0) -> None:
    """Wait until an HTTP MLflow server is ready."""
    if urlparse(tracking_uri).scheme not in {"http", "https"}:
        return

    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with urllib.request.urlopen(tracking_uri, timeout=2.0) as response:
                if response.status < 500:
                    return
        except Exception:
            pass

        if time.monotonic() >= deadline:
            raise TimeoutError(f"MLflow is not ready: {tracking_uri}")
        time.sleep(2.0)


def model_destination_kwargs(mlflow_sklearn: Any, name: str) -> dict[str, str]:
    """Return the supported destination keyword for this MLflow version."""
    parameters = inspect.signature(mlflow_sklearn.log_model).parameters
    if "name" in parameters:
        return {"name": name}
    return {"artifact_path": name}


def load_xy(path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load features and convert the text label to a binary target."""
    dataframe = pd.read_csv(path)
    return dataframe.loc[:, list(FEATURE_COLUMNS)], (
        dataframe[TARGET_COLUMN] == POSITIVE_LABEL
    ).astype(int)


def sample_xy(
    features: pd.DataFrame,
    labels: pd.Series,
    sample_size: int,
    random_state: int,
) -> tuple[pd.DataFrame, pd.Series]:
    """Keep demo training bounded on small classroom VMs."""
    if sample_size <= 0 or len(features) <= sample_size:
        return features, labels

    sampled_index = features.sample(n=sample_size, random_state=random_state).index
    return features.loc[sampled_index], labels.loc[sampled_index]


def build_model(
    *,
    n_estimators: int,
    max_depth: int,
    random_state: int,
) -> Pipeline:
    """Build the sklearn pipeline used by the trainer."""
    return Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    max_depth=max_depth,
                    min_samples_leaf=5,
                    random_state=random_state,
                    n_jobs=1,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def train_once(config: TrainConfig, run_index: int) -> dict[str, object]:
    """Train one model, log it to MLflow, and save it for the API."""
    import mlflow
    import mlflow.sklearn

    seed = int(time.time()) % 1_000_000 + run_index
    max_depth = 4 + (seed % 3)

    train_x, train_y = load_xy(config.train_path)
    test_x, test_y = load_xy(config.test_path)
    train_x, train_y = sample_xy(
        train_x,
        train_y,
        config.train_sample_size,
        random_state=seed,
    )
    test_x, test_y = sample_xy(
        test_x,
        test_y,
        config.test_sample_size,
        random_state=seed + 1,
    )

    model = build_model(
        n_estimators=config.n_estimators,
        max_depth=max_depth,
        random_state=seed,
    )
    model.fit(train_x, train_y)

    probabilities = model.predict_proba(test_x)[:, 1]
    predictions = (probabilities >= DEFAULT_THRESHOLD).astype(int)
    metrics = {
        "accuracy": accuracy_score(test_y, predictions),
        "precision": precision_score(test_y, predictions, zero_division=0),
        "recall": recall_score(test_y, predictions, zero_division=0),
        "f1": f1_score(test_y, predictions, zero_division=0),
    }
    params = {
        "features": ",".join(FEATURE_COLUMNS),
        "label": TARGET_COLUMN,
        "positive_label": POSITIVE_LABEL,
        "threshold": DEFAULT_THRESHOLD,
        "model_type": "RandomForestClassifier",
        "n_estimators": config.n_estimators,
        "max_depth": max_depth,
        "seed": seed,
        "train_rows": len(train_x),
        "test_rows": len(test_x),
    }

    now = datetime.now(UTC).isoformat()
    mlflow.set_tracking_uri(config.tracking_uri)
    mlflow.set_experiment(config.experiment)
    with mlflow.start_run(run_name=f"train-{now}") as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            sk_model=model,
            input_example=test_x.head(3),
            **model_destination_kwargs(mlflow.sklearn, "model"),
        )
        metadata = {
            "trained_at": now,
            "run_id": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "tracking_uri": config.tracking_uri,
            "features": list(FEATURE_COLUMNS),
            "threshold": DEFAULT_THRESHOLD,
            "metrics": metrics,
            "params": params,
        }

        model_path = Path(config.model_path)
        metadata_path = Path(config.metadata_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "metadata": metadata}, model_path)
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        mlflow.log_artifact(str(metadata_path))

    return metadata
