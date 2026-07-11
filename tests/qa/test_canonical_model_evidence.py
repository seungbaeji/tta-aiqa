"""Canonical one-shot release scenario evidence tests."""

import hashlib
import json
from pathlib import Path


def test_sealed_test_blocks_candidate_b_deployment() -> None:
    evidence = json.loads(
        Path("reference/evidence/model/canonical-benchmark.json").read_text(
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


def test_canonical_evidence_matches_finalized_freeze_manifest() -> None:
    evidence = json.loads(
        Path("reference/evidence/model/canonical-benchmark.json").read_text(
            encoding="utf-8"
        )
    )
    freeze_path = Path(evidence["sealed_test"]["freeze_manifest_path"])
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
