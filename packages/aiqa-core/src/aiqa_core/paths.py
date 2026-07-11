"""Repository path helpers."""

from __future__ import annotations

from pathlib import Path


def project_root(start: Path | None = None) -> Path:
    """Find the repository root from a file or working directory."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "apps").is_dir() and (candidate / "data").is_dir():
            return candidate

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate

    msg = f"Could not find project root from {current}"
    raise FileNotFoundError(msg)


def data_path(*parts: str, root: Path | None = None) -> Path:
    """Return a path under the repository data directory."""
    return (root or project_root()) / "data" / Path(*parts)
