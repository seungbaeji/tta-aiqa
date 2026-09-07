"""MLflow runtime configuration adapter."""

from pathlib import Path
from urllib.parse import urlparse

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
        if urlparse(tracking_uri).scheme in {"http", "https"}:
            client.create_experiment(experiment_name)
        else:
            client.create_experiment(
                experiment_name,
                artifact_location=artifact_root.resolve().as_uri(),
            )
    mlflow.set_experiment(experiment_name)
