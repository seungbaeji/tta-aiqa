"""MLflow sklearn model logging compatibility adapter."""

import inspect

import mlflow.sklearn


def sklearn_model_destination(name: str) -> dict[str, str]:
    """Return the supported MLflow keyword for a logged sklearn model artifact."""
    parameters = inspect.signature(mlflow.sklearn.log_model).parameters
    return {"name" if "name" in parameters else "artifact_path": name}
