"""Optional MLflow experiment tracker."""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ai_quality.common.paths import artifact_path
from ai_quality.model_quality.ports.experiment_tracker import ScalarValue


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
    ) -> Path | None:
        """Log one run to MLflow if the package is installed."""
        try:
            import mlflow
        except ModuleNotFoundError:
            return None

        tracking_uri = self.tracking_uri or f"sqlite:///{artifact_path('mlflow.db')}"
        try:
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(self.experiment_name)

            with mlflow.start_run(run_name=run_name):
                for key, value in params.items():
                    mlflow.log_param(key, value)
                for key, value in metrics.items():
                    mlflow.log_metric(key, value)
                for path in artifacts:
                    if path.exists():
                        try:
                            mlflow.log_artifact(str(path))
                        except Exception as error:
                            warnings.warn(
                                f"Skipping artifact logging for '{path}' due to MLflow upload error: {error}"
                            )

            return artifact_path("mlflow.db")
        except Exception as error:
            warnings.warn(
                f"Skipping MLflow tracking due to exception: {type(error).__name__}: {error}"
            )
            return None


def mlflow_available() -> bool:
    """Return whether MLflow can be imported."""
    try:
        import mlflow  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True
