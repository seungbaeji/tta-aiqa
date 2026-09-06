"""Git source-identity adapter for pre-test release provenance."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

FROZEN_SOURCE_PATHS = (
    "apps",
    "packages",
    "configs",
    "deploy",
    "scripts",
    "dvc.yaml",
    "params.yaml",
    "pyproject.toml",
    "uv.lock",
)


@dataclass(frozen=True)
class GitRevision:
    """A resolved Git object ID used as one release source identity."""

    commit: str

    def __post_init__(self) -> None:
        is_lowercase_sha = all(
            character in "0123456789abcdef" for character in self.commit
        )
        if len(self.commit) not in {40, 64} or not is_lowercase_sha:
            raise ValueError("Git revision must be a lowercase Git object ID")


@dataclass(frozen=True)
class GitSourceRevisionControl:
    """Git-backed source identity capability bound to one repository root."""

    repository_root: Path

    def capture(self) -> str:
        """Return the current commit without requiring a clean worktree."""
        return capture_revision(self.repository_root).commit

    def capture_clean(self) -> str:
        """Return the current commit only when the worktree is clean."""
        return capture_clean_revision(self.repository_root).commit

    def verify(self, frozen_commit: str) -> None:
        """Verify a clean source tree unchanged at runtime paths since the freeze."""
        verify_frozen_revision(frozen_commit, self.repository_root)


def capture_revision(repository_root: Path) -> GitRevision:
    """Resolve the current Git commit without imposing a release cleanliness policy."""
    output = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return GitRevision(output.stdout.strip())


def capture_clean_revision(repository_root: Path) -> GitRevision:
    """Resolve a commit only when the repository has no uncommitted changes."""
    status = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout:
        raise RuntimeError("release freeze requires a clean Git worktree")
    return capture_revision(repository_root)


def verify_frozen_revision(frozen_commit: str, repository_root: Path) -> None:
    """Require a clean tree with no runtime source change since the frozen commit."""
    current = capture_clean_revision(repository_root)
    ancestry = subprocess.run(
        ("git", "merge-base", "--is-ancestor", frozen_commit, current.commit),
        cwd=repository_root,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        raise RuntimeError("frozen Git commit is not an ancestor of the current source")
    difference = subprocess.run(
        (
            "git",
            "diff",
            "--quiet",
            frozen_commit,
            current.commit,
            "--",
            *FROZEN_SOURCE_PATHS,
        ),
        cwd=repository_root,
        capture_output=True,
        text=True,
    )
    if difference.returncode == 1:
        raise RuntimeError(
            "source or versioned configuration changed since release freeze"
        )
    if difference.returncode != 0:
        raise RuntimeError("could not verify frozen Git source identity")
