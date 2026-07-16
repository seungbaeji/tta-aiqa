"""Guard writes to immutable course evidence from maintenance scripts."""

from __future__ import annotations

import argparse
from pathlib import Path


def add_output_arguments(
    parser: argparse.ArgumentParser,
    *,
    root: Path,
    default_relative_path: str,
) -> None:
    """Add an opt-in historical output contract to a maintenance CLI parser."""
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "artifacts/evidence-drafts" / default_relative_path,
        help=(
            "write a review draft here; use --write-historical-evidence to target "
            "docs/reference/evidence"
        ),
    )
    parser.add_argument(
        "--write-historical-evidence",
        action="store_true",
        help="allow --output below docs/reference/evidence after an explicit review",
    )


def resolve_output_path(
    *,
    root: Path,
    output: Path,
    write_historical_evidence: bool,
) -> Path:
    """Return a resolved output path or reject an accidental historical rewrite."""
    resolved_output = output.expanduser().resolve()
    historical_root = (root / "docs/reference/evidence").resolve()
    if _is_within(resolved_output, historical_root) and not write_historical_evidence:
        raise ValueError(
            "refusing to overwrite historical evidence; write a draft outside "
            "docs/reference/evidence or pass --write-historical-evidence explicitly"
        )
    return resolved_output


def _is_within(path: Path, parent: Path) -> bool:
    """Return whether a resolved path is contained by a resolved parent directory."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
