"""Official source acquisition and checksum contract tests."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from aiqa_data.adapters import (
    acquire_source_manifest,
    verify_source_manifest,
    write_source_integrity_report,
)


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
    assert verify_source_manifest(manifest).files[0].path == "source.bin"


def test_acquisition_rejects_payload_before_replacing_destination(
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path, b"expected")

    with pytest.raises(ValueError, match="size mismatch"):
        acquire_source_manifest(manifest, fetch=lambda _: b"bad")

    assert not (tmp_path / "source.bin").exists()


def test_typed_source_integrity_report_serializes_to_course_evidence(
    tmp_path: Path,
) -> None:
    payload = b"official-source"
    manifest = write_manifest(tmp_path, payload)
    acquire_source_manifest(manifest, fetch=lambda _: payload)
    report = verify_source_manifest(manifest)
    evidence_path = tmp_path / "source-integrity.json"

    write_source_integrity_report(report, evidence_path)

    document = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert document["verified"] is True
    assert document["dataset"]["name"] == "fixture"
    assert document["files"] == [
        {
            "path": "source.bin",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    ]
