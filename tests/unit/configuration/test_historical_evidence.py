"""Safety contracts for maintenance-only evidence builders."""

from pathlib import Path

import pytest

from scripts.historical_evidence import resolve_output_path


def test_historical_evidence_requires_explicit_rewrite_flag(tmp_path: Path) -> None:
    """Tracked evidence cannot be overwritten by a maintenance command by default."""
    root = tmp_path
    historical_output = root / "docs/reference/evidence/model/canonical-benchmark.json"

    with pytest.raises(ValueError, match="refusing to overwrite historical evidence"):
        resolve_output_path(
            root=root,
            output=historical_output,
            write_historical_evidence=False,
        )


def test_explicit_rewrite_and_draft_output_are_distinguished(tmp_path: Path) -> None:
    """An explicit rewrite remains possible while drafts stay unrestricted."""
    root = tmp_path
    historical_output = root / "docs/reference/evidence/model/canonical-benchmark.json"
    draft_output = root / "artifacts/evidence-drafts/model/canonical-benchmark.json"

    assert resolve_output_path(
        root=root,
        output=historical_output,
        write_historical_evidence=True,
    ) == historical_output.resolve()
    assert resolve_output_path(
        root=root,
        output=draft_output,
        write_historical_evidence=False,
    ) == draft_output.resolve()
