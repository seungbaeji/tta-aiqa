"""Versioned PhysioNet source contract tests."""

from pathlib import Path

import pytest
from aiqa_data.adapters import load_source_contract, verify_source_manifest
from aiqa_data.adapters.physionet import parse_record


def test_official_source_files_match_versioned_manifest() -> None:
    source = load_source_contract(Path("configs/contracts/physionet-record.yaml"))

    evidence = verify_source_manifest(source.source_manifest_path)

    assert [item.path for item in evidence.files] == [
        "set-a.zip",
        "Outcomes-a.txt",
    ]
    assert source.expected_record_count == 4000
    assert source.expected_death_count == 554


def test_record_parser_rejects_observation_after_configured_window(
    tmp_path: Path,
) -> None:
    path = tmp_path / "7.txt"
    path.write_text(
        "Time,Parameter,Value\n00:00,RecordID,7\n48:01,HR,90\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exceeds configured window"):
        parse_record(path, max_minute=48 * 60)
