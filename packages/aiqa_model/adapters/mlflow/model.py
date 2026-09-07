"""MLflow tracking adapter for serialized sklearn model bundles."""

from collections.abc import Mapping
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.models import infer_signature
from sklearn.pipeline import Pipeline

from aiqa_model.adapters.mlflow.contracts import (
    MODEL_ARTIFACT_NAME,
    PHYSIONET_2012_DATASET_NAME,
    TRAIN_INPUT_NAME,
    TRAINING_INPUT_CONTEXT,
    VALID_INPUT_NAME,
    VALIDATION_INPUT_CONTEXT,
)
from aiqa_model.adapters.mlflow.datasets import (
    local_dataset_source,
    mlflow_dataset_digest,
)
from aiqa_model.adapters.mlflow.models import sklearn_model_destination
from aiqa_model.adapters.mlflow.runtime import configure_tracking
from aiqa_model.domain import MetricAtStep, ModelProfile, ProfileEvaluation


class MlflowModelTracker:
    """Record a fitted sklearn pipeline, datasets, and bundle artifacts in MLflow."""

    def __init__(
        self,
        tracking_uri: str,
        experiment_name: str,
        artifact_root: Path,
    ) -> None:
        """Bind the tracker to one MLflow server and experiment name."""
        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name
        self._artifact_root = artifact_root

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
        extra_tags: Mapping[str, str] | None = None,
        run_name: str | None = None,
        metric_history: tuple[MetricAtStep, ...] = (),
    ) -> str:
        """Log one model, its train/valid inputs, metrics, and external bundle files."""
        configure_tracking(
            self._tracking_uri,
            self._experiment_name,
            self._artifact_root,
        )
        train = pd.read_csv(train_path)
        valid = pd.read_csv(valid_path)
        feature_columns = [
            column for column in valid.columns if column not in {"record_id", "target"}
        ]
        with mlflow.start_run(
            run_name=run_name or f"model-{profile.name}"
        ) as run:
            mlflow.set_tags(
                {
                    "aiqa.profile": profile.name,
                    "aiqa.model_role": profile.model_role.value,
                    "aiqa.candidate_id": profile.candidate_id or "",
                    "aiqa.evaluation_role": "valid",
                    "aiqa.dataset": PHYSIONET_2012_DATASET_NAME,
                    **dict(extra_tags or {}),
                }
            )
            mlflow.log_params(
                {
                    "model_kind": profile.kind.value,
                    "threshold": profile.threshold,
                    **{
                        f"model.{key}": tracking_param_value(value)
                        for key, value in profile.params
                    },
                    **provenance,
                }
            )
            scalar_metrics = {
                "valid.precision": evaluation.metrics.precision,
                "valid.recall": evaluation.metrics.recall,
                "valid.f1": evaluation.metrics.f1,
                "valid.roc_auc": evaluation.metrics.roc_auc,
                "valid.pr_auc": evaluation.metrics.pr_auc,
                "valid.false_negative": evaluation.metrics.false_negative,
                "valid.recall_ci_lower": evaluation.bootstrap_recall_lower,
            }
            history_names = {item.name for item in metric_history}
            if metric_history:
                for item in metric_history:
                    mlflow.log_metric(item.name, item.value, step=item.step)
                for name, value in scalar_metrics.items():
                    if name not in history_names:
                        mlflow.log_metric(name, value)
            else:
                mlflow.log_metrics(scalar_metrics)
            mlflow.log_input(
                mlflow.data.from_pandas(
                    train.drop(columns=["record_id"]).astype(float),
                    source=local_dataset_source(train_path),
                    targets="target",
                    name=TRAIN_INPUT_NAME,
                    digest=mlflow_dataset_digest(provenance.get("train_data_hash")),
                ),
                context=TRAINING_INPUT_CONTEXT,
            )
            mlflow.log_input(
                mlflow.data.from_pandas(
                    valid.drop(columns=["record_id"]).astype(float),
                    source=local_dataset_source(valid_path),
                    targets="target",
                    name=VALID_INPUT_NAME,
                    digest=mlflow_dataset_digest(provenance.get("valid_data_hash")),
                ),
                context=VALIDATION_INPUT_CONTEXT,
            )
            mlflow.log_artifacts(str(bundle_dir), artifact_path="bundle")
            input_example = valid[feature_columns].head(3).astype(float)
            mlflow.sklearn.log_model(
                sk_model=pipeline,
                input_example=input_example,
                signature=infer_signature(
                    input_example, pipeline.predict(input_example).astype(float)
                ),
                serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
                **sklearn_model_destination(MODEL_ARTIFACT_NAME),
            )
            return run.info.run_id


def tracking_param_value(value: object) -> str | int | float:
    """Convert profile parameters into MLflow-supported scalar param values."""
    if isinstance(value, bool) or value is None:
        return str(value)
    if isinstance(value, (int, float, str)):
        return value
    return str(value)
