"""Official source acquisition and checksum contract tests."""

import hashlib
from pathlib import Path

import pytest
import yaml
from aiqa_data.adapters import acquire_source_manifest, verify_source_manifest


def write_manifest(root: Path, payload: bytes) -> Path:
    manifest = {
        "schema_version": 1,
        "dataset": {
            "name": "fixture",
            "challenge": "fixture",
            "version": "1.0.0",
            "subset": "Set A",
            "homepage": "https://example.test",
            "retrieved_on": "2026-07-11",
        },
        "license": {
            "name": "fixture",
            "identifier": "fixture",
            "url": "https://example.test/license",
        },
        "citation": {"text": "fixture", "doi": "https://example.test/doi"},
        "files": [
            {
                "path": "source.bin",
                "source_url": "https://example.test/source.bin",
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ],
    }
    path = root / "source-manifest.yaml"
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (root / "LICENSE.txt").write_text("fixture license\n", encoding="utf-8")
    return path


def test_acquisition_downloads_verifies_and_reuses_official_file(
    tmp_path: Path,
) -> None:
    payload = b"official-source"
    manifest = write_manifest(tmp_path, payload)
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return payload

    first = acquire_source_manifest(manifest, fetch=fetch)
    second = acquire_source_manifest(
        manifest,
        fetch=lambda _: pytest.fail("verified source must not be downloaded again"),
    )

    assert first == second == (tmp_path / "source.bin",)
    assert calls == ["https://example.test/source.bin"]
    assert verify_source_manifest(manifest)["verified"] is True


def test_acquisition_rejects_payload_before_replacing_destination(
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path, b"expected")

    with pytest.raises(ValueError, match="size mismatch"):
        acquire_source_manifest(manifest, fetch=lambda _: b"bad")

    assert not (tmp_path / "source.bin").exists()
