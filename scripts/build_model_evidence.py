"""Promote one-shot model benchmark artifacts to prepared evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from aiqa_qa.adapters import load_release_policy
from aiqa_qa.domain import ModelEvidence, decide_release

if __package__:
    from .historical_evidence import add_output_arguments, resolve_output_path
else:
    from historical_evidence import add_output_arguments, resolve_output_path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    """Return the SHA-256 digest for a binary file."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_evidence(profile: dict[str, Any]) -> ModelEvidence:
    """Convert serialized benchmark metrics to the release-policy domain value."""
    metrics = profile["metrics"]
    return ModelEvidence(
        profile=profile["profile"],
        precision=metrics["precision"],
        recall=metrics["recall"],
        pr_auc=metrics["pr_auc"],
        false_negative=metrics["false_negative"],
        bootstrap_recall_lower=profile["bootstrap_recall_lower"],
    )


def parse_args() -> argparse.Namespace:
    """Parse a maintenance-only model evidence output request."""
    parser = argparse.ArgumentParser(description=__doc__)
    add_output_arguments(
        parser,
        root=ROOT,
        default_relative_path="model/canonical-benchmark.json",
    )
    args = parser.parse_args()
    try:
        args.output = resolve_output_path(
            root=ROOT,
            output=args.output,
            write_historical_evidence=args.write_historical_evidence,
        )
    except ValueError as error:
        parser.error(str(error))
    return args


def main() -> None:
    """Build V1 model-evidence drafts without rewriting tracked evidence by default."""
    args = parse_args()
    development_path = ROOT / "artifacts/model/development-benchmark.json"
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    prepared_development_path = output.parent / "development-benchmark.json"
    final_path = ROOT / "artifacts/model/final-benchmark.json"
    policy_path = ROOT / "configs/qa/release-policy.yaml"
    freeze_path = ROOT / "docs/reference/evidence/model/release-freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    frozen_paths = {
        "feature_contract_path": ROOT / "configs/contracts/model-input.yaml",
        "feature_sets_path": ROOT / "configs/model/feature-sets.yaml",
        "profiles_path": ROOT / "configs/model/profiles.yaml",
        "evaluation_path": ROOT / "configs/model/evaluation.yaml",
        "release_policy_path": policy_path,
        "train_dataset": ROOT / "data/splits/physionet-2012/datasets/train.csv",
        "valid_dataset": ROOT / "data/splits/physionet-2012/datasets/valid.csv",
        "development_evidence": development_path,
    }
    actual_frozen_hashes = {name: sha256(path) for name, path in frozen_paths.items()}
    if actual_frozen_hashes != freeze["sha256"]:
        raise ValueError("current inputs do not match the pre-test freeze manifest")
    prepared_development_path.write_text(
        development_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    final = json.loads(final_path.read_text(encoding="utf-8"))
    if final["evaluation_role"] != "test" or final["accessed_roles"] != [
        "train",
        "valid",
        "test",
    ]:
        raise ValueError("final benchmark does not prove the canonical role boundary")

    policy = load_release_policy(policy_path)
    profiles = {item["profile"]: item for item in final["profiles"]}
    baseline = model_evidence(profiles[policy.baseline_profile])
    decisions = [
        decide_release(policy, baseline, model_evidence(profiles[name]))
        for name in (
            policy.candidate_a_profile,
            policy.candidate_b_profile,
        )
    ]
    deployment_allowed = all(
        item.decision.value == expected
        for item, expected in zip(decisions, ("HOLD", "APPROVE"), strict=True)
    )
    document = {
        "schema_version": 1,
        "status": "APPROVED" if deployment_allowed else "SCENARIO_REVIEW_REQUIRED",
        "deployment_allowed": deployment_allowed,
        "sealed_test": {
            "status": "evaluated_once",
            "artifact_sha256": sha256(final_path),
            "accessed_roles": final["accessed_roles"],
            "freeze_manifest_persisted_before_test": True,
            "freeze_manifest_path": "docs/reference/evidence/model/release-freeze.json",
            "freeze_manifest_sha256": sha256(freeze_path),
            "protocol_exception": None,
        },
        "configuration": {
            "feature_contract_sha256": sha256(
                ROOT / "configs/contracts/model-input.yaml"
            ),
            "profiles_sha256": sha256(ROOT / "configs/model/profiles.yaml"),
            "evaluation_sha256": sha256(ROOT / "configs/model/evaluation.yaml"),
            "release_policy_sha256": sha256(policy_path),
            "development_benchmark_sha256": sha256(development_path),
        },
        "profiles": final["profiles"],
        "decisions": [
            {
                "profile": item.profile,
                "decision": item.decision.value,
                "checks": dict(item.checks),
            }
            for item in decisions
        ],
        "required_follow_up": (
            "Do not deploy Candidate B and do not tune policy, features, threshold, or "
            "model profiles against the sealed test. Review the teaching scenario."
        ),
    }
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
