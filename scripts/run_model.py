"""Cross-platform entry point for revisioned canonical model workflows."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RevisionPaths:
    profiles: Path
    evaluation: Path
    feature_sets: Path
    release_policy: Path
    split_dataset_dir: Path
    data_manifest: Path
    evidence_root: Path
    artifact_root: Path
    model_root: Path


def revision_paths(revision: str) -> RevisionPaths:
    if revision == "v1":
        return RevisionPaths(
            profiles=ROOT / "configs/model/profiles.yaml",
            evaluation=ROOT / "configs/model/evaluation.yaml",
            feature_sets=ROOT / "configs/model/feature-sets.yaml",
            release_policy=ROOT / "configs/qa/release-policy.yaml",
            split_dataset_dir=ROOT / "data/splits/physionet-2012/datasets",
            data_manifest=(
                ROOT / "docs/reference/evidence/data-lineage/data-manifest.json"
            ),
            evidence_root=ROOT / "docs/reference/evidence/model",
            artifact_root=ROOT / "artifacts/model",
            model_root=ROOT / "artifacts/models",
        )
    return RevisionPaths(
        profiles=ROOT / "configs/model/revisions/v2/profiles.yaml",
        evaluation=ROOT / "configs/model/revisions/v2/evaluation.yaml",
        feature_sets=ROOT / "configs/model/revisions/v2/feature-sets.yaml",
        release_policy=ROOT / "configs/qa/revisions/v2.yaml",
        split_dataset_dir=ROOT / "data/splits/physionet-2012/revisions/v2/datasets",
        data_manifest=(
            ROOT / "docs/reference/evidence/data-lineage/split-revision-v2.json"
        ),
        evidence_root=ROOT / "docs/reference/evidence/model/revisions/v2",
        artifact_root=ROOT / "artifacts/model/revisions/v2",
        model_root=ROOT / "artifacts/models/revisions/v2",
    )


def environment(revision: str) -> dict[str, str]:
    paths = revision_paths(revision)
    mlflow_dir = ROOT / "artifacts/mlflow"
    mlflow_dir.mkdir(parents=True, exist_ok=True)
    values = {
        "REPOSITORY_ROOT": ROOT,
        "FEATURE_CONTRACT_PATH": ROOT / "configs/contracts/model-input.yaml",
        "FEATURE_SETS_PATH": paths.feature_sets,
        "PROFILES_PATH": paths.profiles,
        "EVALUATION_PATH": paths.evaluation,
        "RELEASE_POLICY_PATH": paths.release_policy,
        "SPLIT_DATASET_DIR": paths.split_dataset_dir,
        "SPLIT_CONFIG_PATH": ROOT / "params.yaml",
        "DATA_MANIFEST_PATH": paths.data_manifest,
        "DVC_LOCK_PATH": ROOT / "dvc.lock",
        "ARTIFACT_DIR": paths.artifact_root,
        "DEVELOPMENT_EVIDENCE_PATH": paths.evidence_root / "development-benchmark.json",
        "FEATURE_DIAGNOSTICS_PATH": paths.evidence_root / "feature-diagnostics.json",
        "MODEL_BUNDLE_DIR": paths.model_root / "bundles",
        "DEPLOYED_MODEL_DIR": paths.model_root / "deployed",
        "BOOTSTRAP_MANIFEST_PATH": paths.artifact_root / "model-bootstrap.json",
        "BOOTSTRAP_EVIDENCE_PATH": paths.evidence_root / "model-bootstrap.json",
        "FREEZE_MANIFEST_PATH": paths.evidence_root / "release-freeze.json",
        "RELEASE_MANIFEST_PATH": paths.evidence_root / "release-manifest.json",
        "CANONICAL_EVIDENCE_PATH": paths.evidence_root / "canonical-benchmark.json",
    }
    result = os.environ.copy()
    result.update(
        {f"AIQA_MODEL_{key}": str(value.resolve()) for key, value in values.items()}
    )
    result["AIQA_MODEL_MLFLOW_TRACKING_URI"] = (
        f"sqlite:///{(mlflow_dir / 'mlflow.db').resolve().as_posix()}"
    )
    result["AIQA_MODEL_MLFLOW_EXPERIMENT_NAME"] = f"tta-aiqa-physionet-2012-{revision}"
    return result


def show_status(revision: str) -> None:
    path = revision_paths(revision).evidence_root / "canonical-benchmark.json"
    if not path.exists():
        print(json.dumps({"revision": revision, "status": "NOT_EVALUATED"}, indent=2))
        return
    document = json.loads(path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "revision": revision,
                "status": document["status"],
                "deployment_allowed": document["deployment_allowed"],
                "sealed_test": document["sealed_test"]["status"],
                "decisions": {
                    item["profile"]: item["decision"] for item in document["decisions"]
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "status",
            "development",
            "diagnostics",
            "bootstrap",
            "reconcile-bootstrap",
            "final",
            "reconcile-final",
        ),
    )
    parser.add_argument("--revision", choices=("v1", "v2"), default="v2")
    parser.add_argument("--sealed-test-token")
    args = parser.parse_args()
    if args.command == "status":
        show_status(args.revision)
        return
    command = ["uv", "run", "aiqa-model-trainer", args.command]
    if args.command == "final":
        if args.sealed_test_token is None:
            parser.error("final requires --sealed-test-token")
        command.extend(("--sealed-test-token", args.sealed_test_token))
    subprocess.run(
        command,
        cwd=ROOT / "artifacts",
        env=environment(args.revision),
        check=True,
    )


if __name__ == "__main__":
    main()
