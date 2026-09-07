"""Canonical one-shot release scenario evidence tests."""

import hashlib
import json
from pathlib import Path


def test_sealed_test_blocks_candidate_b_deployment() -> None:
    evidence = json.loads(
        Path("docs/evidence/model-v1/canonical-benchmark.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["sealed_test"]["status"] == "evaluated_once"
    assert evidence["deployment_allowed"] is False
    assert evidence["status"] == "SCENARIO_REVIEW_REQUIRED"
    assert {item["profile"]: item["decision"] for item in evidence["decisions"]} == {
        "candidate-a": "HOLD",
        "candidate-b": "HOLD",
    }
    candidate_b = next(
        item for item in evidence["decisions"] if item["profile"] == "candidate-b"
    )
    assert candidate_b["checks"]["pr_auc_vs_baseline"] is False


CURRENT_FREEZE_MANIFESTS = {
    "reference/evidence/model/release-freeze.json": Path(
        "docs/evidence/model-v1/release-freeze.json"
    ),
    "reference/evidence/model/revisions/v2/release-freeze.json": Path(
        "docs/evidence/model-v2/release-freeze.json"
    ),
}


def recorded_freeze_manifest(recorded_path: str) -> Path:
    """Resolve a frozen provenance path without rewriting canonical JSON."""
    return CURRENT_FREEZE_MANIFESTS.get(recorded_path, Path("docs") / recorded_path)


def test_canonical_evidence_matches_finalized_freeze_manifest() -> None:
    evidence = json.loads(
        Path("docs/evidence/model-v1/canonical-benchmark.json").read_text(
            encoding="utf-8"
        )
    )
    # Canonical evidence preserves the repository-relative path recorded when it
    # was generated. Historical evidence now lives below docs/ without rewriting
    # that provenance payload.
    freeze_path = recorded_freeze_manifest(
        evidence["sealed_test"]["freeze_manifest_path"]
    )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))

    assert evidence["sealed_test"]["freeze_manifest_persisted_before_test"] is True
    assert evidence["sealed_test"]["protocol_exception"] is None
    assert (
        hashlib.sha256(freeze_path.read_bytes()).hexdigest()
        == (evidence["sealed_test"]["freeze_manifest_sha256"])
    )
    assert freeze["sealed_test_status"] == "evaluated_once"
    assert freeze["release_status"] == "scenario_review"
    assert freeze["model_bundles"] == {}
