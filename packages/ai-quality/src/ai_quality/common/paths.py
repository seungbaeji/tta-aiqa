"""Project path helpers."""

from __future__ import annotations

from pathlib import Path


def project_root(start: Path | None = None) -> Path:
    """Find the workspace root that owns course data and configs."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "configs").is_dir() and (candidate / "data").is_dir():
            return candidate

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate

    msg = f"Could not find project root from {current}"
    raise FileNotFoundError(msg)


def data_path(*parts: str) -> Path:
    """Return a path inside the ignored data directory."""
    return project_root() / "data" / Path(*parts)


def config_path(*parts: str) -> Path:
    """Return a path inside the configs directory."""
    return project_root() / "configs" / Path(*parts)


def artifact_path(*parts: str) -> Path:
    """Return a path inside the generated artifacts directory."""
    return project_root() / "artifacts" / Path(*parts)
