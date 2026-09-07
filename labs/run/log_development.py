"""Log one train/valid development run to classroom Compose MLflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from aiqa_core.adapters.config import load_feature_contract
from aiqa_core.domain import FeatureSet
from aiqa_model.adapters import (
    MlflowModelTracker,
    load_evaluation_plan,
    load_model_profiles,
    persist_model_bundle,
)
from aiqa_model.adapters.sklearn.evaluation import SklearnProfileEvaluator
from aiqa_model.adapters.sklearn.pipeline import build_model_pipeline
from aiqa_model.adapters.sklearn.selection import select_profile
from aiqa_model.domain import EvaluationPlan, ModelProfile, ProfileEvaluation
from mlflow.environment_variables import (
    MLFLOW_PRINT_MODEL_URLS_ON_CREATION,
    MLFLOW_SUPPRESS_PRINTING_URL_TO_STDOUT,
)
from sklearn.pipeline import Pipeline

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
    data_revision: str
    tracking_uri_environment_variable: str
    run_name: str
    data_roles: tuple[str, ...]
    paths: dict[str, str]
    tags: dict[str, str]


@dataclass(frozen=True)
class DevelopmentInput:
    """One verified train/valid file declared by the V2 lineage evidence."""

    role: str
    path: Path
    rows: int
    sha256: str


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
    paths = {str(key): str(value) for key, value in dict(document["paths"]).items()}
    required_paths = {
        "train",
        "valid",
        "data_lineage",
        "profiles",
        "evaluation",
        "feature_contract",
        "dvc_lock",
        "release_manifest",
    }
    missing_paths = sorted(required_paths - paths.keys())
    if missing_paths:
        raise ValueError(
            f"student tracking contract is missing paths: {', '.join(missing_paths)}"
        )
    tags = {
        str(key): str(value) for key, value in dict(document["tags"]).items()
    }
    return StudentTrackingContract(
        experiment_name=experiment_name,
        profile_name=str(document["profile_name"]).strip(),
        data_revision=str(document["data_revision"]).strip(),
        tracking_uri_environment_variable=str(
            document["tracking_uri_environment_variable"]
        ).strip(),
        run_name=str(document["run_name"]).strip(),
        data_roles=data_roles,
        paths=paths,
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
    train_path: Path,
    valid_path: Path,
    data_roles: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read exactly the train and valid CSV files that will be logged to MLflow."""
    if tuple(data_roles) != ("train", "valid"):
        raise ValueError("development splits may read only train and valid")
    train = pd.read_csv(train_path)
    valid = pd.read_csv(valid_path)
    required_columns = {"record_id", "target"}
    if not required_columns.issubset(train.columns) or not required_columns.issubset(
        valid.columns
    ):
        raise ValueError("development inputs must contain record_id and target")
    if train.empty or valid.empty:
        raise ValueError("development splits must include both train and valid rows")
    if set(train["record_id"]).intersection(valid["record_id"]):
        raise ValueError("train and valid record IDs must be disjoint")
    return train, valid


def verify_development_lineage(
    root: Path,
    contract: StudentTrackingContract,
) -> tuple[DevelopmentInput, DevelopmentInput]:
    """Verify revision, path, row count, and digest before opening model inputs."""
    lineage_path = root / contract.paths["data_lineage"]
    document = json.loads(lineage_path.read_text(encoding="utf-8"))
    if str(document.get("revision")) != contract.data_revision:
        raise ValueError(
            "student data revision does not match data-lineage evidence"
        )

    verified: list[DevelopmentInput] = []
    role_documents = document.get("role_datasets", {})
    for role in contract.data_roles:
        try:
            role_document = role_documents[role]
        except KeyError:
            raise ValueError(
                f"data-lineage evidence does not define the {role} role"
            ) from None
        relative_path = contract.paths[role]
        if str(role_document.get("path")) != relative_path:
            raise ValueError(
                f"{role} path does not match data-lineage evidence"
            )
        path = root / relative_path
        actual_sha256 = file_sha256(path)
        expected_sha256 = str(role_document.get("sha256"))
        if actual_sha256 != expected_sha256:
            raise RuntimeError(
                f"{role} dataset digest does not match data-lineage evidence"
            )
        if role_document.get("target_included") is not True:
            raise ValueError(f"{role} lineage must include the target")
        verified.append(
            DevelopmentInput(
                role=role,
                path=path,
                rows=int(role_document["rows"]),
                sha256=actual_sha256,
            )
        )
    return verified[0], verified[1]


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


def fit_and_evaluate(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    profile: ModelProfile,
    feature_set: FeatureSet,
    evaluation_plan: EvaluationPlan,
    random_seed: int,
) -> tuple[Pipeline, ProfileEvaluation]:
    """Fit one configured model on train and evaluate that artifact on valid."""
    def pipeline_builder(selected: ModelProfile) -> Pipeline:
        return build_model_pipeline(
            feature_set=feature_set,
            profile=selected,
            random_seed=random_seed,
        )

    pipeline = pipeline_builder(profile)
    pipeline.fit(
        train[list(feature_set.feature_names)],
        train["target"].to_numpy(dtype=int),
    )
    evaluator = SklearnProfileEvaluator(
        feature_names=feature_set.feature_names,
        evaluation_plan=evaluation_plan,
        random_seed=random_seed,
        pipeline_builder=pipeline_builder,
    )
    return pipeline, evaluator.evaluate_fitted(profile, pipeline, valid)


def file_sha256(path: Path) -> str:
    """Return the full SHA-256 identity of one local file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_source_revision(root: Path) -> str:
    """Return the Git commit that owns this student development run."""
    return subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def build_student_provenance(
    *,
    root: Path,
    contract: StudentTrackingContract,
    source_revision: str,
    data_lineage_path: Path,
    train_path: Path,
    valid_path: Path,
) -> dict[str, str]:
    """Build train/valid-only identities for the student MLflow run."""
    return {
        "git_commit": source_revision,
        "data_revision": contract.data_revision,
        "data_roles": ",".join(contract.data_roles),
        "dvc_lock_sha256": file_sha256(root / contract.paths["dvc_lock"]),
        "data_lineage_sha256": file_sha256(data_lineage_path),
        "train_data_hash": file_sha256(train_path),
        "valid_data_hash": file_sha256(valid_path),
        "feature_contract_sha256": file_sha256(
            root / contract.paths["feature_contract"]
        ),
        "model_profile_config_hash": file_sha256(
            root / contract.paths["profiles"]
        ),
    }


def record_student_mlflow_run(
    *,
    tracking_uri: str,
    experiment_name: str,
    profile: ModelProfile,
    evaluation: ProfileEvaluation,
    pipeline: Pipeline,
    bundle_dir: Path,
    train_path: Path,
    valid_path: Path,
    provenance: dict[str, str],
    tags: Mapping[str, str],
    artifact_root: Path,
    run_name: str,
) -> str:
    """Record the same dataset, metric, bundle, and model views used in production."""
    import mlflow

    previous_tracking_uri = mlflow.get_tracking_uri()
    tracker = MlflowModelTracker(
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
        artifact_root=artifact_root,
    )
    try:
        return tracker.record(
            profile=profile,
            evaluation=evaluation,
            pipeline=pipeline,
            bundle_dir=bundle_dir,
            train_path=train_path,
            valid_path=valid_path,
            provenance=provenance,
            extra_tags=dict(tags),
            run_name=run_name,
        )
    finally:
        mlflow.set_tracking_uri(previous_tracking_uri)


def run_student_development(
    *,
    root: Path,
    environ: Mapping[str, str],
    contract_path: Path | None = None,
    health_probe: Callable[[str], bool] | None = None,
    record_run: Callable[..., str] | None = None,
    source_revision: Callable[[Path], str] | None = None,
) -> dict[str, Any]:
    """Train on train/valid and log a student run, or return MLFLOW_NOT_RUNNING."""
    contract = load_contract(contract_path or CONTRACT_PATH)
    official_train_run, official_final_run = read_official_run_ids(
        root / contract.paths["release_manifest"]
    )
    train_input, valid_input = verify_development_lineage(root, contract)
    train, valid = load_development_splits(
        train_input.path,
        valid_input.path,
        contract.data_roles,
    )
    if len(train) != train_input.rows or len(valid) != valid_input.rows:
        raise RuntimeError(
            "development input row count does not match data-lineage evidence"
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
        "profile_name": contract.profile_name,
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
    feature_set = load_feature_contract(root / contract.paths["feature_contract"])
    evaluation_plan = load_evaluation_plan(root / contract.paths["evaluation"])
    pipeline, evaluation = fit_and_evaluate(
        train,
        valid,
        profile,
        feature_set,
        evaluation_plan,
        catalog.random_seed,
    )
    train_path = train_input.path
    valid_path = valid_input.path
    resolve_revision = (
        source_revision if source_revision is not None else capture_source_revision
    )
    provenance = build_student_provenance(
        root=root,
        contract=contract,
        source_revision=resolve_revision(root),
        data_lineage_path=root / contract.paths["data_lineage"],
        train_path=train_path,
        valid_path=valid_path,
    )
    recorder = record_run if record_run is not None else record_student_mlflow_run
    with tempfile.TemporaryDirectory(prefix="aiqa-student-bundle-") as temporary:
        model_path, metadata_path = persist_model_bundle(
            pipeline=pipeline,
            profile=profile,
            evaluation=evaluation,
            feature_set=feature_set,
            feature_contract_sha256=provenance["feature_contract_sha256"],
            provenance=provenance,
            output_dir=Path(temporary),
        )
        student_run_id = recorder(
            tracking_uri=tracking_uri,
            experiment_name=contract.experiment_name,
            profile=profile,
            evaluation=evaluation,
            pipeline=pipeline,
            bundle_dir=model_path.parent,
            train_path=train_path,
            valid_path=valid_path,
            provenance=provenance,
            tags=contract.tags,
            artifact_root=root / "artifacts/mlruns",
            run_name=contract.run_name,
        )
        bundle_model_sha256 = file_sha256(model_path)
        bundle_metadata_sha256 = file_sha256(metadata_path)
    result.update(
        {
            "status": "LOGGED",
            "student_run_id": student_run_id,
            "model_kind": profile.kind.value,
            "threshold": profile.threshold,
            "metrics": {
                f"valid_{name}": value
                for name, value in asdict(evaluation.metrics).items()
            },
            "bundle_model_sha256": bundle_model_sha256,
            "bundle_metadata_sha256": bundle_metadata_sha256,
            "feature_contract_sha256": provenance["feature_contract_sha256"],
            "lineage": provenance,
        }
    )
    return result


def main() -> int:
    """Render one student tracking result as JSON for the course journey."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    # Keep stdout machine-readable for the notebook; the Run URI is in the result.
    MLFLOW_SUPPRESS_PRINTING_URL_TO_STDOUT.set(True)
    MLFLOW_PRINT_MODEL_URLS_ON_CREATION.set(False)
    result = run_student_development(
        root=find_repository_root(),
        environ=os.environ,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
