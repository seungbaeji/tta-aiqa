from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from ai_quality.model_quality.infrastructure import mlflow_tracker
from ai_quality.model_quality.infrastructure.mlflow_tracker import (
    MlflowExperimentTracker,
    is_http_tracking_uri,
    local_mlflow_tracking_uri,
    local_store_path_from_tracking_uri,
)


def install_fake_mlflow(monkeypatch):
    calls: dict[str, object] = {
        "params": {},
        "metrics": {},
        "artifacts": [],
        "tags": {},
    }
    fake = ModuleType("mlflow")

    class FakeActiveRun:
        info = SimpleNamespace(run_id="run-123", experiment_id="exp-7")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def set_tracking_uri(tracking_uri: str) -> None:
        calls["tracking_uri"] = tracking_uri

    def set_experiment(experiment_name: str) -> None:
        calls["experiment_name"] = experiment_name

    def start_run(run_name: str) -> FakeActiveRun:
        calls["run_name"] = run_name
        return FakeActiveRun()

    def set_tags(tags: dict[str, str]) -> None:
        calls["tags"] = tags

    def log_param(key: str, value: object) -> None:
        params = calls["params"]
        assert isinstance(params, dict)
        params[key] = value

    def log_metric(key: str, value: float) -> None:
        metrics = calls["metrics"]
        assert isinstance(metrics, dict)
        metrics[key] = value

    def log_artifact(path: str) -> None:
        artifacts = calls["artifacts"]
        assert isinstance(artifacts, list)
        artifacts.append(path)

    fake.set_tracking_uri = set_tracking_uri
    fake.set_experiment = set_experiment
    fake.start_run = start_run
    fake.set_tags = set_tags
    fake.log_param = log_param
    fake.log_metric = log_metric
    fake.log_artifact = log_artifact
    fake.get_artifact_uri = lambda: "file:///tmp/mlflow-artifacts/run-123"
    fake.data = ModuleType("mlflow.data")

    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.data", fake.data)
    return calls


def test_local_tracking_uri_round_trip(tmp_path: Path) -> None:
    store_path = tmp_path / "mlflow.db"

    tracking_uri = local_mlflow_tracking_uri(store_path)

    assert tracking_uri == f"sqlite:///{store_path.resolve()}"
    assert local_store_path_from_tracking_uri(tracking_uri) == store_path.resolve()
    assert not is_http_tracking_uri(tracking_uri)


def test_log_run_returns_mlflow_record_for_local_store(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = install_fake_mlflow(monkeypatch)
    artifact = tmp_path / "metrics.json"
    artifact.write_text("{}", encoding="utf-8")

    record = MlflowExperimentTracker(
        experiment_name="quality",
        local_store_path=tmp_path / "mlflow.db",
    ).log_run(
        run_name="eval",
        params={"dataset": "test"},
        metrics={"accuracy": 0.9},
        artifacts=[artifact],
        tags={"stage": "qa"},
    )

    assert record is not None
    assert record.tracker == "mlflow"
    assert record.experiment_name == "quality"
    assert record.run_id == "run-123"
    assert record.local_store_path == tmp_path / "mlflow.db"
    assert record.tracking_uri == f"sqlite:///{tmp_path / 'mlflow.db'}"
    assert record.artifact_uri == "file:///tmp/mlflow-artifacts/run-123"
    assert record.ui_url is None
    assert calls["tracking_uri"] == record.tracking_uri
    assert calls["experiment_name"] == "quality"
    assert calls["params"] == {"dataset": "test"}
    assert calls["metrics"] == {"accuracy": 0.9}
    assert calls["tags"] == {"stage": "qa"}
    assert calls["artifacts"] == [str(artifact)]


def test_log_run_returns_remote_run_url(monkeypatch) -> None:
    install_fake_mlflow(monkeypatch)

    record = MlflowExperimentTracker(
        experiment_name="quality",
        tracking_uri="http://127.0.0.1:5001",
    ).log_run(run_name="eval", params={}, metrics={})

    assert record is not None
    assert record.is_remote
    assert record.local_store_path is None
    assert record.ui_url == (
        "http://127.0.0.1:5001/#/experiments/exp-7/runs/run-123"
    )


def test_from_env_can_skip_unready_remote(monkeypatch) -> None:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5999")
    monkeypatch.setattr(
        mlflow_tracker,
        "mlflow_tracking_server_ready",
        lambda tracking_uri, timeout_seconds=2.0: False,
    )

    tracker = MlflowExperimentTracker.from_env(
        "quality",
        fallback_to_local=False,
    )

    assert tracker is None
