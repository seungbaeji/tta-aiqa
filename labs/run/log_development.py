"""Log one train/valid development run to classroom Compose MLflow."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from aiqa_model.adapters.config import load_model_profiles
from aiqa_model.adapters.sklearn.selection import select_profile
from aiqa_model.domain import ModelProfile
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Classroom tracking URI comes from AIQA_MLFLOW_TRACKING_URI. No sqlite or
# localhost default. This module does not write artifacts/mlflow or
# docs/evidence/.
CONTRACT_PATH = Path(__file__).resolve().parent / "development.yaml"
EXCLUDED_COLUMNS = frozenset({"record_id", "target", "role"})
HTTP_SCHEMES = ("http://", "https://")


@dataclass(frozen=True)
class StudentTrackingContract:
    """Versioned student tracking settings owned by labs/run YAML."""

    experiment_name: str
    profile_name: str
    tracking_uri_environment_variable: str
    run_name: str
    data_roles: tuple[str, ...]
    paths: dict[str, str]
    tags: dict[str, str]


def find_repository_root(start: Path | None = None) -> Path:
    """Return the course repository root that owns configs/ and pyproject.toml."""
    here = start if start is not None else Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "configs"
        ).is_dir():
            return candidate
    raise FileNotFoundError("course repository root was not found")


def load_contract(path: Path) -> StudentTrackingContract:
    """Load the student tracking contract and reject official experiment names."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("student tracking contract must be a mapping")
    experiment_name = str(document["experiment_name"]).strip()
    if not experiment_name:
        raise ValueError("experiment_name must be a non-empty string")
    if experiment_name.startswith("tta-aiqa-physionet-2012"):
        raise ValueError("student tracking must not use the official experiment name")
    data_roles = tuple(str(role) for role in document["data_roles"])
    if data_roles != ("train", "valid"):
        raise ValueError("student tracking may access only train and valid roles")
    tags = {
        str(key): str(value) for key, value in dict(document["tags"]).items()
    }
    return StudentTrackingContract(
        experiment_name=experiment_name,
        profile_name=str(document["profile_name"]).strip(),
        tracking_uri_environment_variable=str(
            document["tracking_uri_environment_variable"]
        ).strip(),
        run_name=str(document["run_name"]).strip(),
        data_roles=data_roles,
        paths={str(key): str(value) for key, value in dict(document["paths"]).items()},
        tags=tags,
    )


def read_official_run_ids(manifest_path: Path) -> tuple[str, str]:
    """Read official train and final run IDs without creating new official runs."""
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    approved = document["approved_model"]
    return (
        str(approved["model_mlflow_run_id"]),
        str(approved["final_mlflow_run_id"]),
    )


def load_development_splits(
    features_path: Path,
    split_manifest_path: Path,
    data_roles: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join features to split roles and keep only the contracted development roles."""
    features = pd.read_csv(features_path)
    splits = pd.read_csv(split_manifest_path)
    joined = features.merge(splits, on="record_id", validate="one_to_one")
    development = joined.loc[joined["role"].isin(list(data_roles))].copy()
    train = development.loc[development["role"].eq("train")].copy()
    valid = development.loc[development["role"].eq("valid")].copy()
    if train.empty or valid.empty:
        raise ValueError("development splits must include both train and valid rows")
    return train, valid


def probe_tracking_health(uri: str, timeout_seconds: float = 3.0) -> bool:
    """Return True only when an HTTP(S) tracking URL answers /health."""
    if not uri.startswith(HTTP_SCHEMES):
        return False
    try:
        with urllib.request.urlopen(
            f"{uri.rstrip('/')}/health", timeout=timeout_seconds
        ) as response:
            return 200 <= int(response.status) < 300
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False


def _feature_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in EXCLUDED_COLUMNS]


def fit_and_score(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    profile: ModelProfile,
    random_seed: int,
) -> tuple[dict[str, float], dict[str, object]]:
    """Fit the contracted profile on train and score it on valid only."""
    feature_columns = _feature_columns(train)
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    random_state=random_seed, **profile.parameter_dict()
                ),
            ),
        ]
    )
    model.fit(train[feature_columns], train["target"])
    scores = model.predict_proba(valid[feature_columns])[:, 1]
    predictions = (scores >= profile.threshold).astype(int)
    target = valid["target"].to_numpy(dtype=int)
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        target, predictions, labels=[0, 1]
    ).ravel()
    metrics = {
        "valid_precision": float(precision_score(target, predictions, zero_division=0)),
        "valid_recall": float(recall_score(target, predictions, zero_division=0)),
        "valid_f1": float(f1_score(target, predictions, zero_division=0)),
        "valid_roc_auc": float(roc_auc_score(target, scores)),
        "valid_pr_auc": float(average_precision_score(target, scores)),
        "valid_tn": float(true_negative),
        "valid_fp": float(false_positive),
        "valid_fn": float(false_negative),
        "valid_tp": float(true_positive),
    }
    params: dict[str, object] = {
        "threshold": profile.threshold,
        "random_seed": random_seed,
        **{
            key: ("" if value is None else value)
            for key, value in profile.parameter_dict().items()
        },
    }
    return metrics, params


def record_student_mlflow_run(
    *,
    tracking_uri: str,
    experiment_name: str,
    run_name: str,
    params: Mapping[str, object],
    metrics: Mapping[str, float],
    tags: Mapping[str, str],
) -> str:
    """Record one student run on the supplied tracking URI and restore the prior URI."""
    import mlflow

    previous_tracking_uri = mlflow.get_tracking_uri()
    try:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name) as active_run:
            mlflow.log_params({key: str(value) for key, value in params.items()})
            mlflow.log_metrics(dict(metrics))
            mlflow.set_tags(dict(tags))
            return str(active_run.info.run_id)
    finally:
        mlflow.set_tracking_uri(previous_tracking_uri)


def run_student_development(
    *,
    root: Path,
    environ: Mapping[str, str],
    contract_path: Path | None = None,
    health_probe: Callable[[str], bool] | None = None,
    record_run: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """Train on train/valid and log a student run, or return MLFLOW_NOT_RUNNING."""
    contract = load_contract(contract_path or CONTRACT_PATH)
    official_train_run, official_final_run = read_official_run_ids(
        root / contract.paths["release_manifest"]
    )
    train, valid = load_development_splits(
        root / contract.paths["features"],
        root / contract.paths["split_manifest"],
        contract.data_roles,
    )
    tracking_uri = str(
        environ.get(contract.tracking_uri_environment_variable, "")
    ).strip()
    probe = health_probe if health_probe is not None else probe_tracking_health
    tracking_ready = bool(tracking_uri) and probe(tracking_uri)
    result: dict[str, Any] = {
        "status": "MLFLOW_NOT_RUNNING",
        "tracking_uri": tracking_uri or "(unset)",
        "experiment_name": contract.experiment_name,
        "student_run_id": None,
        "official_train_run": official_train_run,
        "official_final_run": official_final_run,
        "train_rows": int(len(train)),
        "valid_rows": int(len(valid)),
        "accessed_roles": ",".join(contract.data_roles),
    }
    if not tracking_ready:
        result["next_action"] = (
            "강사가 준 AIQA_MLFLOW_TRACKING_URI를 설정하고 "
            "/health가 응답하는지 확인합니다."
        )
        return result

    catalog = load_model_profiles(root / contract.paths["profiles"])
    profile = select_profile(catalog.profiles, contract.profile_name)
    metrics, params = fit_and_score(train, valid, profile, catalog.random_seed)
    tags = {
        **contract.tags,
        "data_roles": ",".join(contract.data_roles),
        "profile": profile.name,
    }
    recorder = record_run if record_run is not None else record_student_mlflow_run
    student_run_id = recorder(
        tracking_uri=tracking_uri,
        experiment_name=contract.experiment_name,
        run_name=contract.run_name,
        params=params,
        metrics=metrics,
        tags=tags,
    )
    result.update(
        {
            "status": "LOGGED",
            "student_run_id": student_run_id,
            "metrics": metrics,
        }
    )
    return result


def main() -> int:
    """Render one student tracking result as JSON for the course journey."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = run_student_development(
        root=find_repository_root(),
        environ=os.environ,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
