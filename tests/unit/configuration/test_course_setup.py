"""Course setup state contract tests."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

import scripts.setup_course as setup_course
from scripts.setup_course import (
    MISSING_BASELINE_MODEL_MESSAGE,
    ensure_traffic_artifact_directory,
    missing_notebook_runtime_modules,
    verify_course_state,
)


def test_course_state_validates_but_does_not_reveal_v2_decisions() -> None:
    state = verify_course_state(require_model=False)

    assert state["canonical_decisions"] == "available_read_only"
    assert "HOLD" not in str(state)
    assert "APPROVE" not in str(state)
    assert state["deployed_model"] == "not_required"
    assert state["notebook_runtime"] == "ready"


def test_notebook_runtime_reports_only_missing_modules() -> None:
    """Course setup names the exact dependency group gap before data preparation."""
    available = {"ipykernel", "nbformat"}

    assert missing_notebook_runtime_modules(
        lambda module: object() if module in available else None
    ) == ("nbclient",)


def test_traffic_artifact_directory_is_created_for_the_host_user(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "artifacts" / "traffic"

    result = ensure_traffic_artifact_directory(directory)

    assert result == directory
    assert directory.is_dir()
    assert directory.stat().st_uid == os.getuid()


def test_existing_traffic_artifacts_and_permissions_are_preserved(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "artifacts" / "traffic"
    directory.mkdir(parents=True, mode=0o750)
    marker = directory / "existing.jsonl"
    marker.write_text("existing learner evidence\n", encoding="utf-8")
    original_mode = stat.S_IMODE(directory.stat().st_mode)

    ensure_traffic_artifact_directory(directory)

    assert marker.read_text(encoding="utf-8") == "existing learner evidence\n"
    assert stat.S_IMODE(directory.stat().st_mode) == original_mode


def test_traffic_artifact_setup_rejects_a_file_or_symlink(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "traffic-file"
    file_path.write_text("keep", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        ensure_traffic_artifact_directory(file_path)
    assert file_path.read_text(encoding="utf-8") == "keep"

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "traffic-link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(RuntimeError, match="symbolic link"):
        ensure_traffic_artifact_directory(link)


def test_main_prepares_the_bind_mount_directory_before_course_scripts(
    monkeypatch,
) -> None:
    events: list[str] = []
    monkeypatch.setattr(sys, "argv", ["setup_course.py", "--data-only"])
    monkeypatch.setattr(setup_course, "assert_notebook_runtime", lambda: None)
    monkeypatch.setattr(
        setup_course,
        "ensure_traffic_artifact_directory",
        lambda: events.append("traffic-directory"),
    )
    monkeypatch.setattr(
        setup_course,
        "run_script",
        lambda name: events.append(name),
    )
    monkeypatch.setattr(
        setup_course,
        "verify_course_state",
        lambda **_kwargs: {"status": "ready"},
    )

    setup_course.main()

    assert events == ["traffic-directory", *setup_course.COURSE_SETUP_SCRIPTS]


def test_missing_baseline_model_is_instructor_scope(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    missing = tmp_path / "metadata.json"
    monkeypatch.setattr(setup_course, "DEPLOYED_MODEL_METADATA", missing)
    monkeypatch.setattr(sys, "argv", ["setup_course.py"])
    monkeypatch.setattr(setup_course, "assert_notebook_runtime", lambda: None)
    monkeypatch.setattr(
        setup_course, "ensure_traffic_artifact_directory", lambda: None
    )
    monkeypatch.setattr(setup_course, "run_script", lambda _name: None)

    with pytest.raises(SystemExit) as exit_info:
        setup_course.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert MISSING_BASELINE_MODEL_MESSAGE in captured.err
    assert "instructor/platform scope" in captured.err
