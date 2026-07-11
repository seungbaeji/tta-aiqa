"""Optional MLflow experiment tracker."""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ai_quality.common.paths import artifact_path
from ai_quality.model_quality.ports.experiment_tracker import (
    DatasetInput,
    ModelArtifact,
    ScalarValue,
)


@dataclass(frozen=True)
class MlflowExperimentTracker:
    """Record experiment context to a local MLflow tracking directory."""

    experiment_name: str
    tracking_uri: str | None = None

    def log_run(
        self,
        run_name: str,
        params: Mapping[str, ScalarValue],
        metrics: Mapping[str, float],
        artifacts: Sequence[Path] = (),
        datasets: Sequence[DatasetInput] = (),
        model_artifact: ModelArtifact | None = None,
        tags: Mapping[str, ScalarValue] | None = None,
    ) -> Path | None:
        """Log one run to MLflow if the package is installed."""
        try:
            import mlflow
            import mlflow.data
        except ModuleNotFoundError:
            return None

        tracking_uri = self.tracking_uri or f"sqlite:///{artifact_path('mlflow.db')}"
        try:
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(self.experiment_name)

            with mlflow.start_run(run_name=run_name):
                mlflow.set_tags(
                    {key: str(value) for key, value in (tags or {}).items()}
                )
                for key, value in params.items():
                    mlflow.log_param(key, value)
                for key, value in metrics.items():
                    mlflow.log_metric(key, value)
                for dataset in datasets:
                    self._log_dataset_input(mlflow, dataset)
                if model_artifact is not None:
                    self._log_model_artifact(mlflow, model_artifact)
                for path in artifacts:
                    if path.exists():
                        try:
                            mlflow.log_artifact(str(path))
                        except Exception as error:
                            warnings.warn(
                                (
                                    f"Skipping artifact logging for '{path}' "
                                    f"due to MLflow upload error: {error}"
                                ),
                                stacklevel=2,
                            )

            return artifact_path("mlflow.db")
        except Exception as error:
            warnings.warn(
                (
                    "Skipping MLflow tracking due to exception: "
                    f"{type(error).__name__}: {error}"
                ),
                stacklevel=2,
            )
            return None

    def _log_dataset_input(self, mlflow: object, dataset: DatasetInput) -> None:
        """Attach one dataset as MLflow run input."""
        try:
            dataframe = dataset.dataframe
            if dataframe is None:
                import pandas as pd

                dataframe = pd.read_csv(dataset.path)

            mlflow_dataset = mlflow.data.from_pandas(
                dataframe,
                source=str(dataset.path),
                targets=dataset.target_column,
                name=dataset.name,
                digest=dataset.digest[:36] if dataset.digest else None,
            )
            mlflow.log_input(
                mlflow_dataset,
                context=dataset.context,
                tags={
                    "dataset_version": dataset.version,
                    "dataset_path": str(dataset.path),
                    "dataset_digest": dataset.digest or "",
                },
            )
        except Exception as error:
            warnings.warn(
                (
                    f"Skipping MLflow dataset input '{dataset.name}' "
                    f"due to error: {error}"
                ),
                stacklevel=2,
            )

    def _log_model_artifact(
        self,
        mlflow: object,
        model_artifact: ModelArtifact,
    ) -> None:
        """Attach a scikit-learn model with signature and examples when possible."""
        if model_artifact.model is None:
            return

        try:
            import mlflow.sklearn
            from mlflow.models import infer_signature

            signature = None
            if (
                model_artifact.input_example is not None
                and model_artifact.output_example is not None
            ):
                signature = infer_signature(
                    model_artifact.input_example,
                    model_artifact.output_example,
                )

            mlflow.sklearn.log_model(
                sk_model=model_artifact.model,
                artifact_path="model",
                signature=signature,
                input_example=model_artifact.input_example,
                serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
                metadata={
                    "model_name": model_artifact.name,
                    "model_version": model_artifact.version,
                    "model_source_path": str(model_artifact.path),
                },
            )
        except Exception as error:
            warnings.warn(
                (
                    f"Skipping MLflow model artifact '{model_artifact.name}' "
                    f"due to error: {error}"
                ),
                stacklevel=2,
            )


def mlflow_available() -> bool:
    """Return whether MLflow can be imported."""
    try:
        import mlflow  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True
