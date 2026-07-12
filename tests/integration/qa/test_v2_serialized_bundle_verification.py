"""V2 serialized deployment artifact migration evidence tests."""

import hashlib
import json
from pathlib import Path

from model_trainer.adapters.documents import ReleaseManifestDocument

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "reference/evidence/model/revisions/v2"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v2_freeze_covers_model_and_external_metadata() -> None:
    freeze_path = EVIDENCE / "release-freeze.json"
    canonical = json.loads(
        (EVIDENCE / "canonical-benchmark.json").read_text(encoding="utf-8")
    )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))

    assert canonical["sealed_test"]["freeze_manifest_sha256"] == sha256(freeze_path)
    assert freeze["artifact_contract_migration"] == {
        "canonical_metrics_unchanged": True,
        "original_release_freeze_sha256": (
            "e91099b2ec96b901776b8c540ded2a7cb1607f9e8c0840d290ae257064f43336"
        ),
        "post_test_tuning_performed": False,
        "reason": "serialized_bundle_and_metadata_integrity_contract",
        "verification_scope": (
            "existing serialized bundles against frozen canonical metrics"
        ),
    }
    assert set(freeze["model_bundles"]) == {
        f"{profile}/{name}"
        for profile in ("baseline", "candidate-a", "candidate-b")
        for name in ("model.joblib", "metadata.json")
    }


def test_local_v2_bundles_match_reviewable_verification_when_available() -> None:
    verification = json.loads(
        (EVIDENCE / "serialized-bundle-verification.json").read_text(
            encoding="utf-8"
        )
    )
    bundle_root = ROOT / "artifacts/models/revisions/v2/bundles"
    if not bundle_root.is_dir():
        return

    for profile, expected in verification["profiles"].items():
        assert (
            sha256(bundle_root / profile / "model.joblib")
            == expected["model_sha256"]
        )
        assert (
            sha256(bundle_root / profile / "metadata.json")
            == expected["metadata_sha256"]
        )


def test_v2_release_manifest_authorizes_only_the_frozen_candidate_b_bundle() -> None:
    """V2 post-test evidence binds approval, final metrics, and bundle identities."""
    manifest_path = EVIDENCE / "release-manifest.json"
    freeze_path = EVIDENCE / "release-freeze.json"
    canonical_path = EVIDENCE / "canonical-benchmark.json"
    final_path = EVIDENCE / "final-benchmark.json"
    manifest = ReleaseManifestDocument.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))

    assert manifest.release_status == "release_approved"
    assert manifest.deployment_allowed is True
    assert manifest.approved_profile == "candidate-b"
    assert manifest.approved_model is not None
    assert manifest.approved_model.profile == "candidate-b"
    assert manifest.freeze_manifest.sha256 == sha256(freeze_path)
    assert manifest.canonical_evidence.sha256 == sha256(canonical_path)
    assert manifest.final_evidence.sha256 == sha256(final_path)
    assert manifest.model_bundles == freeze["model_bundles"]
    assert manifest.historical_reconciliation is not None
    assert (
        manifest.historical_reconciliation.frozen_dvc_lock_snapshot_available is False
    )
