"""Protect the immutable Argo CD course release contract."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
renderer = import_module("scripts.render_argocd_application")


def test_argocd_release_uses_a_full_commit_and_selected_overlay() -> None:
    revision = "a" * 40

    rendered = renderer.render(revision, "candidate-b")
    application = yaml.safe_load(rendered)

    source = application["spec"]["source"]
    assert source["targetRevision"] == revision
    assert source["path"] == "deploy/kubernetes/overlays/candidate-b"
    assert "main" not in rendered
    assert "__TTA_AIQA_" not in rendered


@pytest.mark.parametrize(
    "revision",
    ["main", "feat/v2-monorepo", "ABCDEF", "a" * 39, "a" * 41],
)
def test_argocd_release_rejects_mutable_or_partial_revisions(revision: str) -> None:
    with pytest.raises(ValueError, match="40-character"):
        renderer.render(revision, "baseline")


def test_argocd_release_rejects_unknown_overlay() -> None:
    with pytest.raises(ValueError, match="overlay"):
        renderer.render("b" * 40, "student-experiment")
