"""MLflow runtime configuration adapter."""

from pathlib import Path

import mlflow
from mlflow import MlflowClient


def configure_tracking(
    tracking_uri: str,
    experiment_name: str,
    artifact_root: Path,
) -> None:
    """Select a tracking store and keep new artifacts below the owned root."""
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    if client.get_experiment_by_name(experiment_name) is None:
        client.create_experiment(
            experiment_name,
            artifact_location=artifact_root.resolve().as_uri(),
        )
    mlflow.set_experiment(experiment_name)
