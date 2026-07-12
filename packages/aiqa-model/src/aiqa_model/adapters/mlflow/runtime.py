"""MLflow runtime configuration adapter."""

import mlflow


def configure_tracking(tracking_uri: str, experiment_name: str) -> None:
    """Select the MLflow tracking server and experiment for one lifecycle operation."""
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
