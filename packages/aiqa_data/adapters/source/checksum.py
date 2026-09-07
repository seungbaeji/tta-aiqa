"""Content-digest operations for versioned PhysioNet source files."""

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one immutable source artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    """Return the SHA-256 digest of one source payload before it is persisted."""
    return hashlib.sha256(payload).hexdigest()


def matches_expected_file(
    path: Path,
    *,
    size_bytes: int,
    sha256: str,
) -> bool:
    """Return whether a local file already matches its source-manifest entry."""
    return (
        path.is_file()
        and path.stat().st_size == size_bytes
        and sha256_file(path) == sha256
    )
