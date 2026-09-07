"""Student development tracking belongs in labs/run, not leftover notebooks."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "labs/run/log_development.py"
CONTRACT_PATH = ROOT / "labs/run/development.yaml"
OFFICIAL_EXPERIMENT = "tta-aiqa-physionet-2012-v2"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "log_student_development_run", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


student_run = load_module()


def write_fixture_tree(tmp_path: Path) -> Path:
    features = tmp_path / "data/features.csv"
    splits = tmp_path / "data/splits-v2/split-manifest.csv"
    profiles = tmp_path / "configs/model-v2/profiles.yaml"
    manifest = (
        tmp_path
        / "docs/evidence/model-v2/release-manifest.json"
    )
    features.parent.mkdir(parents=True)
    splits.parent.mkdir(parents=True)
    profiles.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "record_id": [1, 2, 3, 4, 5, 6],
            "feat": [0.1, 0.2, 0.8, 0.9, 0.15, 0.85],
            "target": [0, 0, 1, 1, 0, 1],
        }
    ).to_csv(features, index=False)
    pd.DataFrame(
        {
            "record_id": [1, 2, 3, 4, 5, 6],
            "role": ["train", "train", "train", "train", "valid", "valid"],
        }
    ).to_csv(splits, index=False)
    profiles.write_text(
        (
            "schema_version: 1\n"
            "random_seed: 43\n"
            "profiles:\n"
            "  - name: baseline\n"
            "    model_role: baseline\n"
            "    kind: logistic_regression\n"
            "    threshold: 0.50\n"
            "    params:\n"
            "      C: 1.0\n"
            "      class_weight: null\n"
            "      max_iter: 2000\n"
        ),
        encoding="utf-8",
    )
    manifest.write_text(
        json.dumps(
            {
                "approved_model": {
                    "model_mlflow_run_id": "official-train-run",
                    "final_mlflow_run_id": "official-final-run",
                }
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def write_contract(tmp_path: Path) -> Path:
    path = tmp_path / "student-development-tracking.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "experiment_name": "student-development-tracking",
                "profile_name": "baseline",
                "tracking_uri_environment_variable": "AIQA_MLFLOW_TRACKING_URI",
                "run_name": "student-train-valid",
                "data_roles": ["train", "valid"],
                "paths": {
                    "features": "data/features.csv",
                    "split_manifest": (
                        "data/splits-v2/split-manifest.csv"
                    ),
                    "profiles": "configs/model-v2/profiles.yaml",
                    "release_manifest": (
                        "docs/evidence/model-v2/"
                        "release-manifest.json"
                    ),
                },
                "tags": {
                    "purpose": "student-development-tracking",
                    "not_official_evidence": "true",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_contract_owns_student_experiment_name() -> None:
    contract = student_run.load_contract(CONTRACT_PATH)

    assert contract.experiment_name == "student-development-tracking"
    assert contract.experiment_name != OFFICIAL_EXPERIMENT
    assert contract.profile_name == "baseline"
    assert contract.data_roles == ("train", "valid")
    assert contract.tracking_uri_environment_variable == "AIQA_MLFLOW_TRACKING_URI"


def test_module_source_does_not_default_to_local_or_official_tracking() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "sqlite:///" not in source
    assert "TemporaryDirectory(" not in source
    assert "http://127.0.0.1:5000" not in source
    assert OFFICIAL_EXPERIMENT not in source
    assert "practice-development-tracking" not in source
    assert "AIQA_MLFLOW_TRACKING_URI" in source
    assert "MLFLOW_NOT_RUNNING" in source
    assert "artifacts/mlflow" in source
    assert "docs/evidence/" in source


def test_unset_tracking_uri_does_not_create_a_run(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    recorded: list[Any] = []

    result = student_run.run_student_development(
        root=root,
        environ={},
        contract_path=write_contract(tmp_path),
        record_run=lambda **kwargs: recorded.append(kwargs) or "should-not-run",
    )

    assert result["status"] == "MLFLOW_NOT_RUNNING"
    assert result["student_run_id"] is None
    assert result["official_train_run"] == "official-train-run"
    assert result["official_final_run"] == "official-final-run"
    assert result["train_rows"] == 4
    assert result["valid_rows"] == 2
    assert recorded == []


def test_sqlite_tracking_uri_does_not_create_a_run(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    recorded: list[Any] = []

    result = student_run.run_student_development(
        root=root,
        environ={"AIQA_MLFLOW_TRACKING_URI": "sqlite:////tmp/mlflow.db"},
        contract_path=write_contract(tmp_path),
        record_run=lambda **kwargs: recorded.append(kwargs) or "should-not-run",
    )

    assert result["status"] == "MLFLOW_NOT_RUNNING"
    assert recorded == []


def test_failed_health_does_not_create_a_run(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    recorded: list[Any] = []

    result = student_run.run_student_development(
        root=root,
        environ={"AIQA_MLFLOW_TRACKING_URI": "https://mlflow.example.test"},
        contract_path=write_contract(tmp_path),
        health_probe=lambda _uri: False,
        record_run=lambda **kwargs: recorded.append(kwargs) or "should-not-run",
    )

    assert result["status"] == "MLFLOW_NOT_RUNNING"
    assert recorded == []


def test_ready_tracking_logs_student_run_without_official_ids(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    recorded: list[dict[str, Any]] = []

    result = student_run.run_student_development(
        root=root,
        environ={"AIQA_MLFLOW_TRACKING_URI": "https://mlflow.example.test"},
        contract_path=write_contract(tmp_path),
        health_probe=lambda uri: uri == "https://mlflow.example.test",
        record_run=lambda **kwargs: recorded.append(kwargs) or "student-run-id",
    )

    assert result["status"] == "LOGGED"
    assert result["student_run_id"] == "student-run-id"
    assert result["student_run_id"] != result["official_train_run"]
    assert result["student_run_id"] != result["official_final_run"]
    assert recorded[0]["experiment_name"] == "student-development-tracking"
    assert recorded[0]["tracking_uri"] == "https://mlflow.example.test"
    assert recorded[0]["tags"]["not_official_evidence"] == "true"
    assert recorded[0]["tags"]["data_roles"] == "train,valid"
    assert "artifacts/mlflow" not in str(recorded[0])
    assert "docs/evidence" not in str(recorded[0].get("artifact_path", ""))
    assert recorded[0].get("artifact_path") is None


def test_development_splits_exclude_sealed_roles(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    extra = pd.read_csv(
        root / "data/splits-v2/split-manifest.csv"
    )
    extra.loc[len(extra)] = {"record_id": 7, "role": "test"}
    extra.to_csv(
        root / "data/splits-v2/split-manifest.csv",
        index=False,
    )
    features = pd.read_csv(
        root / "data/features.csv"
    )
    features.loc[len(features)] = {"record_id": 7, "feat": 0.5, "target": 0}
    features.to_csv(
        root / "data/features.csv",
        index=False,
    )

    train, valid = student_run.load_development_splits(
        root / "data/features.csv",
        root / "data/splits-v2/split-manifest.csv",
        ("train", "valid"),
    )

    assert set(train["role"].unique()) == {"train"}
    assert set(valid["role"].unique()) == {"valid"}
    assert 7 not in set(train["record_id"]).union(set(valid["record_id"]))


def test_health_probe_rejects_non_http_uris() -> None:
    assert student_run.probe_tracking_health("") is False
    assert student_run.probe_tracking_health("sqlite:////tmp/mlflow.db") is False
    assert student_run.probe_tracking_health("file:///tmp/mlflow") is False
