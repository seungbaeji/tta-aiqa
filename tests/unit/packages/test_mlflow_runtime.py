"""MLflow runtime keeps remote artifact ownership on the tracking server."""

from pathlib import Path
from typing import Any

from aiqa_model.adapters.mlflow import runtime


class FakeClient:
    """Capture experiment creation without contacting an MLflow server."""

    def __init__(self, *, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri
        self.created: list[tuple[str, dict[str, Any]]] = []

    def get_experiment_by_name(self, _name: str) -> None:
        """Report that the requested experiment does not exist."""
        return None

    def create_experiment(self, name: str, **kwargs: Any) -> None:
        """Record the requested experiment name and storage options."""
        self.created.append((name, kwargs))


def test_remote_tracking_uses_server_default_artifact_destination(
    monkeypatch,
    tmp_path: Path,
) -> None:
    clients: list[FakeClient] = []
    monkeypatch.setattr(runtime.mlflow, "set_tracking_uri", lambda _uri: None)
    monkeypatch.setattr(runtime.mlflow, "set_experiment", lambda _name: None)
    monkeypatch.setattr(
        runtime,
        "MlflowClient",
        lambda *, tracking_uri: clients.append(
            FakeClient(tracking_uri=tracking_uri)
        )
        or clients[-1],
    )

    runtime.configure_tracking(
        "https://mlflow.example.test",
        "student-development-tracking",
        tmp_path / "mlruns",
    )

    assert clients[0].created == [("student-development-tracking", {})]


def test_local_tracking_keeps_artifacts_under_owned_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    clients: list[FakeClient] = []
    monkeypatch.setattr(runtime.mlflow, "set_tracking_uri", lambda _uri: None)
    monkeypatch.setattr(runtime.mlflow, "set_experiment", lambda _name: None)
    monkeypatch.setattr(
        runtime,
        "MlflowClient",
        lambda *, tracking_uri: clients.append(
            FakeClient(tracking_uri=tracking_uri)
        )
        or clients[-1],
    )

    artifact_root = tmp_path / "mlruns"
    runtime.configure_tracking(
        f"sqlite:///{tmp_path / 'mlflow.db'}",
        "local-development",
        artifact_root,
    )

    assert clients[0].created == [
        (
            "local-development",
            {"artifact_location": artifact_root.resolve().as_uri()},
        )
    ]
