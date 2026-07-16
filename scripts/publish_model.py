"""Publish an approved immutable model bundle to the course deployment path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    """Return the SHA-256 digest for one binary artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_bundle_hashes(release: dict[str, object]) -> dict[str, str]:
    """Validate and return the artifact hash map from a release manifest."""
    hashes = release.get("model_bundles")
    if not isinstance(hashes, dict) or not all(
        isinstance(path, str) and isinstance(digest, str)
        for path, digest in hashes.items()
    ):
        raise ValueError("release manifest must contain model bundle hashes")
    return hashes


def assert_candidate_b_is_released(release: dict[str, object]) -> None:
    """Require an explicit post-test Candidate B authorization in the manifest."""
    approved_model = release.get("approved_model")
    if (
        release.get("release_status") != "release_approved"
        or release.get("deployment_allowed") is not True
        or release.get("approved_profile") != "candidate-b"
        or not isinstance(approved_model, dict)
        or approved_model.get("profile") != "candidate-b"
    ):
        raise PermissionError("Candidate B is not approved by the release manifest")


def publish(
    *,
    profile: str,
    source_dir: Path,
    target_dir: Path,
    canonical_path: Path,
    release_manifest_path: Path,
) -> Path:
    """Copy a verified bundle into one deployment directory atomically."""
    if profile not in {"baseline", "candidate-b"}:
        raise ValueError("only baseline and approved Candidate B can be published")
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    decisions = {item["profile"]: item["decision"] for item in canonical["decisions"]}
    if profile == "candidate-b" and (
        canonical.get("deployment_allowed") is not True
        or decisions.get("candidate-b") != "APPROVE"
    ):
        raise PermissionError("Candidate B does not have canonical release approval")

    release = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(release, dict):
        raise ValueError("release manifest root must be a JSON object")
    if profile == "candidate-b":
        assert_candidate_b_is_released(release)
    bundle_hashes = release_bundle_hashes(release)
    source_model = source_dir / profile / "model.joblib"
    source_metadata = source_dir / profile / "metadata.json"
    expected_hash = bundle_hashes.get(f"{profile}/model.joblib")
    expected_metadata_hash = bundle_hashes.get(f"{profile}/metadata.json")
    actual_hash = sha256(source_model)
    if expected_hash != actual_hash:
        raise ValueError("model bundle hash does not match the release manifest")
    if expected_metadata_hash != sha256(source_metadata):
        raise ValueError("model metadata hash does not match the release manifest")

    target_dir.mkdir(parents=True, exist_ok=True)
    temporary_model = target_dir / ".model.joblib.tmp"
    temporary_metadata = target_dir / ".metadata.json.tmp"
    shutil.copy2(source_model, temporary_model)
    shutil.copy2(source_metadata, temporary_metadata)
    os.replace(temporary_model, target_dir / "model.joblib")
    os.replace(temporary_metadata, target_dir / "metadata.json")
    deployment = {
        "schema_version": 1,
        "profile": profile,
        "model_sha256": actual_hash,
        "canonical_evidence_sha256": sha256(canonical_path),
        "release_status": (
            "APPROVE" if profile == "candidate-b" else "BASELINE_ROLLBACK"
        ),
    }
    deployment_path = target_dir / "deployment.json"
    deployment_path.write_text(
        json.dumps(deployment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return deployment_path


def publish_immutable(
    *,
    profile: str,
    source_dir: Path,
    target_root: Path,
    canonical_path: Path,
    release_manifest_path: Path,
    dataset: str,
    revision: str,
) -> Path:
    """Publish a bundle to an idempotent content-addressed course model path."""
    model_hash = sha256(source_dir / profile / "model.joblib")
    target_dir = target_root / dataset / revision / f"{profile}-{model_hash[:12]}"
    deployment_path = target_dir / "deployment.json"
    if target_dir.exists():
        if not deployment_path.is_file():
            raise FileExistsError(f"incomplete immutable model path: {target_dir}")
        if sha256(target_dir / "model.joblib") != model_hash:
            raise FileExistsError(
                f"immutable model path has different content: {target_dir}"
            )
        source_metadata = source_dir / profile / "metadata.json"
        target_metadata = target_dir / "metadata.json"
        if (
            not target_metadata.is_file()
            or sha256(target_metadata) != sha256(source_metadata)
        ):
            raise FileExistsError(
                f"immutable model metadata has different content: {target_dir}"
            )
        return deployment_path
    return publish(
        profile=profile,
        source_dir=source_dir,
        target_dir=target_dir,
        canonical_path=canonical_path,
        release_manifest_path=release_manifest_path,
    )


def main() -> None:
    """Publish the requested V2 course bundle after release-manifest validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=("baseline", "candidate-b"))
    parser.add_argument("--revision", choices=("v2",), default="v2")
    parser.add_argument(
        "--target-root",
        type=Path,
        help="Course model PVC mount; publishes to an immutable hash path",
    )
    args = parser.parse_args()
    revision = args.revision
    source_dir = ROOT / f"artifacts/models/revisions/{revision}/bundles"
    canonical_path = (
        ROOT
        / f"docs/reference/evidence/model/revisions/{revision}/canonical-benchmark.json"
    )
    release_manifest_path = (
        ROOT
        / f"docs/reference/evidence/model/revisions/{revision}/release-manifest.json"
    )
    if not release_manifest_path.exists():
        raise FileNotFoundError(
            "post-test release manifest is required before model publication: "
            f"{release_manifest_path}"
        )
    if args.target_root:
        path = publish_immutable(
            profile=args.profile,
            source_dir=source_dir,
            target_root=args.target_root,
            canonical_path=canonical_path,
            release_manifest_path=release_manifest_path,
            dataset="physionet-2012",
            revision=revision,
        )
    else:
        path = publish(
            profile=args.profile,
            source_dir=source_dir,
            target_dir=ROOT / f"artifacts/models/revisions/{revision}/deployed",
            canonical_path=canonical_path,
            release_manifest_path=release_manifest_path,
        )
    print(path)


if __name__ == "__main__":
    main()
