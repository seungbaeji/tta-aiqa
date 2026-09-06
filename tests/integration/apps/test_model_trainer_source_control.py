"""Git source-identity adapter tests for Model Trainer provenance."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from model_trainer.adapters.source_control import (
    capture_clean_revision,
    verify_frozen_revision,
)


def git(root: Path, *arguments: str) -> None:
    """Run one checked Git command in an isolated repository fixture."""
    subprocess.run(("git", *arguments), cwd=root, check=True, capture_output=True)


def commit(root: Path, message: str) -> None:
    """Commit all fixture changes with a deterministic local identity."""
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=AIQA Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )


def repository(tmp_path: Path) -> Path:
    """Create a minimum Git repository containing one tracked runtime file."""
    root = tmp_path / "repository"
    (root / "apps").mkdir(parents=True)
    (root / "apps" / "runtime.py").write_text("value = 1\n", encoding="utf-8")
    git(root, "init")
    commit(root, "initial source")
    return root


def test_evidence_only_commit_keeps_frozen_source_valid(tmp_path: Path) -> None:
    """Generated release evidence may be committed without changing source identity."""
    root = repository(tmp_path)
    revision = capture_clean_revision(root)
    evidence = root / "reference" / "evidence" / "release-freeze.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    commit(root, "record freeze")

    verify_frozen_revision(revision.commit, root)


def test_runtime_source_change_invalidates_frozen_revision(tmp_path: Path) -> None:
    """A later runtime change cannot open the sealed test under an old freeze."""
    root = repository(tmp_path)
    revision = capture_clean_revision(root)
    (root / "apps" / "runtime.py").write_text("value = 2\n", encoding="utf-8")
    commit(root, "change runtime")

    with pytest.raises(RuntimeError, match="source or versioned configuration changed"):
        verify_frozen_revision(revision.commit, root)
