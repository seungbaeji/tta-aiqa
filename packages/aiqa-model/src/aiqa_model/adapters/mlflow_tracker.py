"""MLflow benchmark tracking adapter."""

from __future__ import annotations

import inspect
from dataclasses import asdict
from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.data.dataset_source_registry import get_registered_sources
from mlflow.models import infer_signature
from sklearn.pipeline import Pipeline

from aiqa_model.domain import BenchmarkResult, ModelProfile, ProfileEvaluation


class MlflowBenchmarkTracker:
    def __init__(self, tracking_uri: str, experiment_name: str) -> None:
        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name

    def record(
        self,
        result: BenchmarkResult,
        evidence_path: Path,
        provenance: dict[str, str],
    ) -> tuple[str, ...]:
        mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(self._experiment_name)
        run_ids: list[str] = []
        for evaluation in result.profiles:
            with mlflow.start_run(
                run_name=f"{result.evaluation_role}-{evaluation.profile}"
            ) as run:
                mlflow.set_tags(
                    {
                        "aiqa.profile": evaluation.profile,
                        "aiqa.evaluation_role": result.evaluation_role,
                        "aiqa.accessed_roles": ",".join(result.accessed_roles),
                        "aiqa.dataset": "physionet-2012-set-a",
                        **{f"aiqa.{key}": value for key, value in provenance.items()},
                    }
                )
                mlflow.log_param("threshold", evaluation.threshold)
                mlflow.log_metrics(
                    {
                        **{
                            name: float(value)
                            for name, value in asdict(evaluation.metrics).items()
                        },
                        "bootstrap_recall_lower": (evaluation.bootstrap_recall_lower),
                    }
                )
                mlflow.log_artifact(str(evidence_path), artifact_path="evidence")
                run_ids.append(run.info.run_id)
        return tuple(run_ids)


class MlflowModelTracker:
    def __init__(self, tracking_uri: str, experiment_name: str) -> None:
        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name

    def record(
        self,
        *,
        profile: ModelProfile,
        evaluation: ProfileEvaluation,
        pipeline: Pipeline,
        bundle_dir: Path,
        train_path: Path,
        valid_path: Path,
        provenance: dict[str, str],
    ) -> str:
        mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(self._experiment_name)
        train = pd.read_csv(train_path)
        valid = pd.read_csv(valid_path)
        feature_columns = [
            column for column in valid.columns if column not in {"record_id", "target"}
        ]
        with mlflow.start_run(run_name=f"model-{profile.name}") as run:
            mlflow.set_tags(
                {
                    "aiqa.profile": profile.name,
                    "aiqa.model_role": profile.model_role.value,
                    "aiqa.candidate_id": profile.candidate_id or "",
                    "aiqa.evaluation_role": "valid",
                    "aiqa.dataset": "physionet-2012-set-a",
                }
            )
            mlflow.log_params(
                {
                    "model_kind": profile.kind.value,
                    "threshold": profile.threshold,
                    **{f"model.{key}": value for key, value in profile.params},
                    **provenance,
                }
            )
            mlflow.log_metrics(
                {
                    "valid.precision": evaluation.metrics.precision,
                    "valid.recall": evaluation.metrics.recall,
                    "valid.f1": evaluation.metrics.f1,
                    "valid.roc_auc": evaluation.metrics.roc_auc,
                    "valid.pr_auc": evaluation.metrics.pr_auc,
                    "valid.false_negative": evaluation.metrics.false_negative,
                    "valid.recall_ci_lower": evaluation.bootstrap_recall_lower,
                }
            )
            mlflow.log_input(
                mlflow.data.from_pandas(
                    train.drop(columns=["record_id"]).astype(float),
                    source=_local_dataset_source(train_path),
                    targets="target",
                    name="train",
                    digest=_dataset_digest(provenance.get("train_data_hash")),
                ),
                context="training",
            )
            mlflow.log_input(
                mlflow.data.from_pandas(
                    valid.drop(columns=["record_id"]).astype(float),
                    source=_local_dataset_source(valid_path),
                    targets="target",
                    name="valid",
                    digest=_dataset_digest(provenance.get("valid_data_hash")),
                ),
                context="validation",
            )
            mlflow.log_artifacts(str(bundle_dir), artifact_path="bundle")
            input_example = valid[feature_columns].head(3).astype(float)
            mlflow.sklearn.log_model(
                sk_model=pipeline,
                input_example=input_example,
                signature=infer_signature(
                    input_example, pipeline.predict(input_example).astype(float)
                ),
                serialization_format=(mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE),
                **_model_destination("model"),
            )
            return run.info.run_id


def _model_destination(name: str) -> dict[str, Any]:
    parameters = inspect.signature(mlflow.sklearn.log_model).parameters
    return {"name" if "name" in parameters else "artifact_path": name}


def _local_dataset_source(path: Path) -> Any:
    source_class = next(
        source
        for source in get_registered_sources()
        if source.__name__ == "LocalArtifactDatasetSource"
    )
    return source_class(path.resolve().as_uri())


def _dataset_digest(value: str | None) -> str | None:
    return value[:32] if value else None
