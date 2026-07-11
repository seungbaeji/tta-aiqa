"""Shared helpers for chapter 2 labs."""

from __future__ import annotations

import hashlib
import os
import urllib.request
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ai_quality.common.config import load_yaml
from ai_quality.common.paths import artifact_path, config_path, data_path
from ai_quality.model_quality.application.evaluate_classifier import (
    calculate_binary_metrics,
)
from ai_quality.model_quality.domain.evaluation_report import EvaluationReport
from ai_quality.model_quality.infrastructure.json_experiment_tracker import (
    JsonExperimentTracker,
)
from ai_quality.model_quality.infrastructure.mlflow_tracker import (
    MlflowExperimentTracker,
)
from ai_quality.model_quality.infrastructure.sklearn_classifier import (
    load_model,
    predict_positive_scores,
)
from ai_quality.model_quality.ports.experiment_tracker import (
    DatasetInput,
    ModelArtifact,
)


@dataclass(frozen=True)
class EvaluationRecordResult:
    """Paths and metrics created by the chapter 2 evaluation recording step."""

    report: EvaluationReport
    json_path: Path
    mlflow_path: Path | None
    mlflow_tracking_uri: str | None
    dataset_version: str
    dataset_digest: str
    model_version: str


def resolve_mlflow_tracking_uri() -> str | None:
    """Return optional MLflow tracking URI from environment."""
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        return None

    try:
        with urllib.request.urlopen(tracking_uri, timeout=2.0) as response:
            if response.status != 200:
                warnings.warn(
                    (
                        f"MLFLOW_TRACKING_URI '{tracking_uri}' is not ready "
                        f"(HTTP {response.status}). "
                        "Skip MLflow tracking."
                    ),
                    stacklevel=2,
                )
                return None
    except Exception as error:
        warnings.warn(
            (
                f"Could not connect to MLFLOW_TRACKING_URI '{tracking_uri}': "
                f"{type(error).__name__}: {error}. "
                "Skip MLflow tracking."
            ),
            stacklevel=2,
        )
        return None
    return tracking_uri


def load_feature_config() -> dict[str, Any]:
    """Load model feature configuration."""
    return load_yaml(config_path("validation", "model_features.yaml"))


def load_threshold_config() -> dict[str, Any]:
    """Load threshold configuration."""
    return load_yaml(config_path("validation", "model_thresholds.yaml"))


def feature_columns() -> list[str]:
    """Return configured model feature columns."""
    return list(load_feature_config()["feature_columns"])


def target_column() -> str:
    """Return configured target column."""
    return str(load_feature_config()["target_column"])


def threshold_candidates() -> list[float]:
    """Return configured threshold candidates."""
    config = load_threshold_config()
    return [float(value) for value in config["candidate_thresholds"]]


def operating_threshold() -> float:
    """Return configured operating threshold."""
    return float(load_threshold_config()["operating_threshold"])


def chapter_model_path() -> Path:
    """Return the chapter 2 model artifact path."""
    return artifact_path("models", "chapter_02_baseline.pkl")


def dataset_path(filename: str) -> Path:
    """Return a prepared dataset path or raise a helpful error."""
    path = data_path(filename)
    if not path.exists():
        msg = (
            f"Dataset not found: {path}\n"
            "Run: uv run python labs/prepare_data.py"
        )
        raise FileNotFoundError(msg)
    return path


def load_dataset(filename: str) -> pd.DataFrame:
    """Load a prepared CSV dataset."""
    return pd.read_csv(dataset_path(filename))


def file_sha256(path: Path) -> str:
    """Return a stable content digest for a local artifact or dataset."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def print_report(report: EvaluationReport) -> None:
    """Print a compact QA-oriented report."""
    matrix = report.confusion_matrix
    metrics = report.metrics

    print(f"dataset={report.dataset_name}")
    print(f"threshold={report.threshold:.2f}")
    print(f"row_count={report.row_count}")
    print(
        "confusion_matrix="
        f"TP:{matrix.true_positive} "
        f"FP:{matrix.false_positive} "
        f"FN:{matrix.false_negative} "
        f"TN:{matrix.true_negative}"
    )
    print(
        "metrics="
        f"accuracy:{metrics.accuracy:.4f} "
        f"precision:{metrics.precision:.4f} "
        f"recall:{metrics.recall:.4f} "
        f"f1:{metrics.f1_score:.4f} "
        f"auroc:{metrics.auroc or 0.0:.4f} "
        f"pr_auc:{metrics.pr_auc or 0.0:.4f}"
    )


def record_model_test_evaluation() -> EvaluationRecordResult:
    """Evaluate the scikit-learn baseline and record comparison context."""
    test_dataset_path = dataset_path("vital_signs_test.csv")
    dataframe = pd.read_csv(test_dataset_path)
    features = feature_columns()
    target = target_column()
    threshold = operating_threshold()
    model_path = chapter_model_path()
    model = load_model(model_path)
    scores = predict_positive_scores(model, dataframe, features)
    report = calculate_binary_metrics(
        labels=list(dataframe[target]),
        scores=scores,
        threshold=threshold,
        dataset_name="vital_signs_test",
    )

    dataset_digest = file_sha256(test_dataset_path)
    dataset_version = f"v1-test+sha256:{dataset_digest[:12]}"
    model_version = "v1"
    input_example = dataframe.loc[:, features].head(5)
    output_example = model.predict_proba(input_example)[:, 1]
    params = {
        "dataset_name": report.dataset_name,
        "dataset_version": dataset_version,
        "dataset_digest": dataset_digest,
        "dataset_source_path": str(test_dataset_path),
        "model_name": "chapter_02_baseline",
        "model_version": model_version,
        "model_artifact_path": str(model_path),
        "feature_columns": ",".join(features),
        "label_mapping": "High Risk=high_risk, Low Risk=low_risk",
        "operating_threshold": threshold,
    }
    metrics = {
        "accuracy": report.metrics.accuracy,
        "precision": report.metrics.precision,
        "recall": report.metrics.recall,
        "f1_score": report.metrics.f1_score,
        "auroc": report.metrics.auroc or 0.0,
        "pr_auc": report.metrics.pr_auc or 0.0,
        "false_positive": float(report.confusion_matrix.false_positive),
        "false_negative": float(report.confusion_matrix.false_negative),
    }
    datasets = [
        DatasetInput(
            name=report.dataset_name,
            version=dataset_version,
            path=test_dataset_path,
            context="evaluation",
            target_column=target,
            digest=dataset_digest,
            dataframe=dataframe,
        )
    ]
    model_artifact = ModelArtifact(
        name="chapter_02_baseline",
        version=model_version,
        path=model_path,
        model=model,
        input_example=input_example,
        output_example=output_example,
    )
    tags = {
        "course_chapter": "02",
        "qa_stage": "model_quality",
        "dataset_name": report.dataset_name,
        "dataset_version": dataset_version,
        "model_name": "chapter_02_baseline",
        "model_version": model_version,
        "run_purpose": "test_evaluation_record",
    }

    json_path = JsonExperimentTracker.for_chapter("chapter_02").log_run(
        run_name="model_test_eval",
        params=params,
        metrics=metrics,
        artifacts=[model_path],
        datasets=datasets,
        model_artifact=model_artifact,
        tags=tags,
    )
    mlflow_tracking_uri = resolve_mlflow_tracking_uri()

    mlflow_path = MlflowExperimentTracker(
        "ai-quality-chapter-02",
        tracking_uri=mlflow_tracking_uri,
    ).log_run(
        run_name="model_test_eval",
        params=params,
        metrics=metrics,
        artifacts=[json_path, model_path],
        datasets=datasets,
        model_artifact=model_artifact,
        tags=tags,
    )

    return EvaluationRecordResult(
        report=report,
        json_path=json_path,
        mlflow_path=mlflow_path,
        mlflow_tracking_uri=mlflow_tracking_uri,
        dataset_version=dataset_version,
        dataset_digest=dataset_digest,
        model_version=model_version,
    )
