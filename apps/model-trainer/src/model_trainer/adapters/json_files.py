"""JSON and digest operations at the Model Trainer filesystem boundary."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one immutable filesystem artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_mapping(path: Path) -> dict[str, object]:
    """Read one JSON object and reject arrays or scalar documents at this boundary."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"JSON evidence must be an object: {path}")
    return document


def write_json_mapping(document: Mapping[str, object], path: Path) -> Path:
    """Persist a reviewable JSON object using deterministic formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def relative_path(path: Path, root: Path) -> str:
    """Return a path relative to the configured repository root."""
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        raise ValueError(f"artifact is outside the repository root: {path}") from None


def resolve_relative_path(path: str, root: Path) -> Path:
    """Resolve a document path only when it remains inside the repository root."""
    resolved_root = root.resolve()
    resolved_path = (resolved_root / path).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError(f"artifact path escapes the repository root: {path}")
    return resolved_path


@dataclass(frozen=True)
class JsonFileDocumentStore:
    """Filesystem implementation of the Model Trainer JSON document port."""

    def read(self, path: Path) -> dict[str, object]:
        """Load one JSON object from a configured evidence or artifact path."""
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError(f"JSON evidence must be an object: {path}")
        return document

    def write(self, document: Mapping[str, object], path: Path) -> Path:
        """Persist one JSON object using the trainer's deterministic JSON format."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
