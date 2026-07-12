"""Approved model publication gate tests."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts.publish_model import publish, publish_immutable, sha256


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_documents(tmp_path: Path, approved: bool = True) -> tuple[Path, Path, Path]:
    source = tmp_path / "bundles"
    for profile in ("baseline", "candidate-b"):
        directory = source / profile
        directory.mkdir(parents=True)
        model = f"{profile}-model".encode()
        (directory / "model.joblib").write_bytes(model)
        (directory / "metadata.json").write_text("{}\n", encoding="utf-8")
    canonical = tmp_path / "canonical.json"
    canonical.write_text(
        json.dumps(
            {
                "deployment_allowed": approved,
                "decisions": [
                    {
                        "profile": "candidate-b",
                        "decision": "APPROVE" if approved else "HOLD",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    release = tmp_path / "release.json"
    release.write_text(
        json.dumps(
            {
                "model_bundles": {
                    f"{profile}/{name}": digest((source / profile / name).read_bytes())
                    for profile in ("baseline", "candidate-b")
                    for name in ("model.joblib", "metadata.json")
                }
            }
        ),
        encoding="utf-8",
    )
    return source, canonical, release


def test_candidate_b_publication_requires_approval_and_matching_hash(
    tmp_path: Path,
) -> None:
    source, canonical, release = write_documents(tmp_path)
    target = tmp_path / "deployed"

    deployment = publish(
        profile="candidate-b",
        source_dir=source,
        target_dir=target,
        canonical_path=canonical,
        release_manifest_path=release,
    )

    assert json.loads(deployment.read_text())["release_status"] == "APPROVE"
    assert (target / "model.joblib").read_bytes() == b"candidate-b-model"


def test_held_candidate_and_unlisted_profile_cannot_be_published(
    tmp_path: Path,
) -> None:
    source, canonical, release = write_documents(tmp_path, approved=False)

    with pytest.raises(PermissionError, match="does not have canonical"):
        publish(
            profile="candidate-b",
            source_dir=source,
            target_dir=tmp_path / "deployed",
            canonical_path=canonical,
            release_manifest_path=release,
        )
    with pytest.raises(ValueError, match="only baseline"):
        publish(
            profile="candidate-a",
            source_dir=source,
            target_dir=tmp_path / "deployed",
            canonical_path=canonical,
            release_manifest_path=release,
        )


def test_immutable_publish_uses_model_hash_and_is_idempotent(
    tmp_path: Path,
) -> None:
    source, canonical, release = write_documents(tmp_path)
    target_root = tmp_path / "course-model-pvc"

    first = publish_immutable(
        profile="candidate-b",
        source_dir=source,
        target_root=target_root,
        canonical_path=canonical,
        release_manifest_path=release,
        dataset="physionet-2012",
        revision="v2",
    )
    second = publish_immutable(
        profile="candidate-b",
        source_dir=source,
        target_root=target_root,
        canonical_path=canonical,
        release_manifest_path=release,
        dataset="physionet-2012",
        revision="v2",
    )

    expected = sha256(source / "candidate-b/model.joblib")[:12]
    assert first == second
    assert first.parent.name == f"candidate-b-{expected}"
    assert (first.parent / "metadata.json").is_file()


def test_publish_rejects_metadata_not_frozen_by_release_manifest(
    tmp_path: Path,
) -> None:
    source, canonical, release = write_documents(tmp_path)
    (source / "candidate-b/metadata.json").write_text(
        '{"tampered": true}\n', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="metadata hash"):
        publish(
            profile="candidate-b",
            source_dir=source,
            target_dir=tmp_path / "deployed",
            canonical_path=canonical,
            release_manifest_path=release,
        )
