"""Student development tracking belongs in labs/run, not leftover notebooks."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml
from mlflow import MlflowClient

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
    splits = tmp_path / "data/splits-v2"
    lineage = tmp_path / "docs/evidence/data-v2/split-revision.json"
    profiles = tmp_path / "configs/model-v2/profiles.yaml"
    evaluation = tmp_path / "configs/model-v2/evaluation.yaml"
    feature_contract = tmp_path / "configs/contracts/model-input.yaml"
    dvc_lock = tmp_path / "dvc.lock"
    manifest = (
        tmp_path
        / "docs/evidence/model-v2/release-manifest.json"
    )
    splits.mkdir(parents=True)
    lineage.parent.mkdir(parents=True)
    profiles.parent.mkdir(parents=True)
    evaluation.parent.mkdir(parents=True, exist_ok=True)
    feature_contract.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    feature_frame = pd.DataFrame(
        {
            "record_id": [1, 2, 3, 4, 5, 6],
            "feat": [0.1, 0.2, 0.8, 0.9, 0.15, 0.85],
            "target": [0, 0, 1, 1, 0, 1],
        }
    )
    train_path = splits / "train.csv"
    valid_path = splits / "valid.csv"
    feature_frame.iloc[:4].to_csv(train_path, index=False)
    feature_frame.iloc[4:].to_csv(valid_path, index=False)
    lineage.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "revision": "v2",
                "role_datasets": {
                    "train": {
                        "path": "data/splits-v2/train.csv",
                        "rows": 4,
                        "sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
                        "target_included": True,
                    },
                    "valid": {
                        "path": "data/splits-v2/valid.csv",
                        "rows": 2,
                        "sha256": hashlib.sha256(valid_path.read_bytes()).hexdigest(),
                        "target_included": True,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    profiles.write_text(
        (
            "schema_version: 1\n"
            "random_seed: 43\n"
            "profiles:\n"
            "  - name: candidate-b\n"
            "    model_role: candidate\n"
            "    candidate_id: candidate-b\n"
            "    kind: random_forest\n"
            "    threshold: 0.35\n"
            "    params:\n"
            "      n_estimators: 10\n"
            "      min_samples_leaf: 1\n"
            "      max_features: sqrt\n"
            "      class_weight: balanced_subsample\n"
            "      n_jobs: 1\n"
        ),
        encoding="utf-8",
    )
    evaluation.write_text(
        (
            "schema_version: 1\n"
            "cross_validation:\n"
            "  splits: 2\n"
            "  repeats: 1\n"
            "  random_seed: 43\n"
            "bootstrap:\n"
            "  iterations: 20\n"
            "  confidence_level: 0.95\n"
            "ranking_metrics: [pr_auc, roc_auc]\n"
            "operating_metrics: [precision, recall, f1, confusion_matrix]\n"
        ),
        encoding="utf-8",
    )
    feature_contract.write_text(
        (
            "schema_version: 1\n"
            "name: test-contract\n"
            "target: target\n"
            "features:\n"
            "  - name: feat\n"
            "    dtype: float\n"
            "    nullable: false\n"
        ),
        encoding="utf-8",
    )
    dvc_lock.write_text("schema: '2.0'\nstages: {}\n", encoding="utf-8")
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
                "profile_name": "candidate-b",
                "data_revision": "v2",
                "tracking_uri_environment_variable": "AIQA_MLFLOW_TRACKING_URI",
                "run_name": "student-mlp-train-valid",
                "data_roles": ["train", "valid"],
                "paths": {
                    "train": "data/splits-v2/train.csv",
                    "valid": "data/splits-v2/valid.csv",
                    "data_lineage": (
                        "docs/evidence/data-v2/split-revision.json"
                    ),
                    "profiles": "configs/model-v2/profiles.yaml",
                    "evaluation": "configs/model-v2/evaluation.yaml",
                    "feature_contract": "configs/contracts/model-input.yaml",
                    "dvc_lock": "dvc.lock",
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
    assert contract.profile_name == "candidate-c"
    assert contract.data_revision == "v2"
    assert contract.data_roles == ("train", "valid")
    assert contract.tracking_uri_environment_variable == "AIQA_MLFLOW_TRACKING_URI"
    assert contract.run_name == "student-mlp-train-valid"
    assert contract.paths["profiles"] == "configs/model-v2/student-profiles.yaml"


def test_module_source_does_not_default_to_local_or_official_tracking() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "sqlite:///" not in source
    assert 'TemporaryDirectory(prefix="mlflow-' not in source
    assert 'TemporaryDirectory(prefix="aiqa-student-bundle-")' in source
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

    def record(**kwargs: Any) -> str:
        bundle_dir = Path(kwargs["bundle_dir"])
        recorded.append(
            {
                **kwargs,
                "bundle_files": sorted(path.name for path in bundle_dir.iterdir()),
                "metadata": json.loads(
                    (bundle_dir / "metadata.json").read_text(encoding="utf-8")
                ),
            }
        )
        return "student-run-id"

    result = student_run.run_student_development(
        root=root,
        environ={"AIQA_MLFLOW_TRACKING_URI": "https://mlflow.example.test"},
        contract_path=write_contract(tmp_path),
        health_probe=lambda uri: uri == "https://mlflow.example.test",
        record_run=record,
        source_revision=lambda _root: "a" * 40,
    )

    assert result["status"] == "LOGGED"
    assert result["student_run_id"] == "student-run-id"
    assert result["student_run_id"] != result["official_train_run"]
    assert result["student_run_id"] != result["official_final_run"]
    assert recorded[0]["experiment_name"] == "student-development-tracking"
    assert recorded[0]["tracking_uri"] == "https://mlflow.example.test"
    assert recorded[0]["profile"].name == "candidate-b"
    assert recorded[0]["profile"].kind.value == "random_forest"
    assert recorded[0]["profile"].threshold == 0.35
    assert recorded[0]["evaluation"].profile == "candidate-b"
    assert recorded[0]["bundle_files"] == ["metadata.json", "model.joblib"]
    assert recorded[0]["metadata"]["profile"] == "candidate-b"
    assert recorded[0]["metadata"]["provenance"]["git_commit"] == "a" * 40
    assert recorded[0]["provenance"]["data_roles"] == "train,valid"
    assert recorded[0]["provenance"]["data_revision"] == "v2"
    assert recorded[0]["provenance"]["dvc_lock_sha256"] == hashlib.sha256(
        (root / "dvc.lock").read_bytes()
    ).hexdigest()
    assert recorded[0]["provenance"]["train_data_hash"]
    assert recorded[0]["provenance"]["valid_data_hash"]
    assert recorded[0]["provenance"]["data_lineage_sha256"]
    assert recorded[0]["provenance"]["feature_contract_sha256"]
    assert "artifacts/mlflow" not in str(recorded[0])
    assert "docs/evidence" not in str(recorded[0].get("artifact_path", ""))
    assert recorded[0].get("artifact_path") is None
    assert result["profile_name"] == "candidate-b"
    assert result["model_kind"] == "random_forest"
    assert result["threshold"] == 0.35
    assert result["bundle_model_sha256"]
    assert result["bundle_metadata_sha256"]
    assert result["lineage"]["git_commit"] == "a" * 40


def test_development_splits_read_only_declared_role_files(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    (root / "data/splits-v2/test.csv").write_text(
        "record_id,feat,target\n7,0.5,0\n",
        encoding="utf-8",
    )

    train, valid = student_run.load_development_splits(
        root / "data/splits-v2/train.csv",
        root / "data/splits-v2/valid.csv",
        ("train", "valid"),
    )

    assert set(train["record_id"]) == {1, 2, 3, 4}
    assert set(valid["record_id"]) == {5, 6}
    assert 7 not in set(train["record_id"]).union(set(valid["record_id"]))


def test_declared_data_revision_must_match_lineage_evidence(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    lineage_path = root / "docs/evidence/data-v2/split-revision.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    lineage["revision"] = "v3"
    lineage_path.write_text(json.dumps(lineage), encoding="utf-8")

    with pytest.raises(ValueError, match="data revision"):
        student_run.run_student_development(
            root=root,
            environ={},
            contract_path=write_contract(tmp_path),
        )


def test_modified_role_file_is_rejected_before_tracking(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    train_path = root / "data/splits-v2/train.csv"
    train_path.write_text(
        f"{train_path.read_text(encoding='utf-8')}7,0.5,0\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="train dataset digest"):
        student_run.run_student_development(
            root=root,
            environ={},
            contract_path=write_contract(tmp_path),
        )


@pytest.mark.integration
def test_student_run_records_inputs_metrics_bundle_and_model(tmp_path: Path) -> None:
    root = write_fixture_tree(tmp_path)
    tracking_uri = f"sqlite:///{tmp_path / 'student-mlflow.db'}"

    result = student_run.run_student_development(
        root=root,
        environ={"AIQA_MLFLOW_TRACKING_URI": tracking_uri},
        contract_path=write_contract(tmp_path),
        health_probe=lambda _uri: True,
        source_revision=lambda _root: "a" * 40,
    )

    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(result["student_run_id"])
    artifact_paths = [item.path for item in client.list_artifacts(run.info.run_id)]
    logged_models = list(
        client.search_logged_models(
            experiment_ids=[run.info.experiment_id],
            filter_string=f"source_run_id = '{run.info.run_id}'",
        )
    )
    downloaded = client.download_artifacts(
        run.info.run_id,
        "bundle/metadata.json",
        str(tmp_path / "downloaded"),
    )
    metadata = json.loads(Path(downloaded).read_text(encoding="utf-8"))

    assert result["status"] == "LOGGED"
    assert run.data.tags["aiqa.profile"] == "candidate-b"
    assert run.data.tags["not_official_evidence"] == "true"
    assert run.data.params["model_kind"] == "random_forest"
    assert run.data.params["threshold"] == "0.35"
    assert run.data.params["dvc_lock_sha256"] == result["lineage"]["dvc_lock_sha256"]
    assert "valid.recall" in run.data.metrics
    assert "valid.pr_auc" in run.data.metrics
    assert len(run.inputs.dataset_inputs) == 2
    assert {
        item.dataset.name for item in run.inputs.dataset_inputs
    } == {"train", "valid"}
    assert "bundle" in artifact_paths
    assert len(logged_models) == 1
    assert logged_models[0].source_run_id == run.info.run_id
    assert metadata["profile"] == "candidate-b"
    assert metadata["model_sha256"] == result["bundle_model_sha256"]


def test_health_probe_rejects_non_http_uris() -> None:
    assert student_run.probe_tracking_health("") is False
    assert student_run.probe_tracking_health("sqlite:////tmp/mlflow.db") is False
    assert student_run.probe_tracking_health("file:///tmp/mlflow") is False
