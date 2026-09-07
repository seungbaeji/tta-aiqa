"""Protect the immutable Argo CD course release contract."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
renderer = import_module("scripts.platform.render_argocd_application")

STUDENT_APP = "tta-aiqa-student-201"
STUDENT_SERVER = "https://10.99.0.201:6443"
IN_CLUSTER_SERVER = "https://kubernetes.default.svc"


def _student_kwargs() -> dict[str, str]:
    return {
        "application_name": STUDENT_APP,
        "destination_namespace": "tta-aiqa",
        "destination_server": STUDENT_SERVER,
    }


def test_argocd_release_uses_a_full_commit_and_selected_overlay() -> None:
    revision = "a" * 40

    rendered = renderer.render(revision, "candidate-b", **_student_kwargs())
    application = yaml.safe_load(rendered)

    source = application["spec"]["source"]
    destination = application["spec"]["destination"]
    assert application["metadata"]["name"] == STUDENT_APP
    assert source["targetRevision"] == revision
    assert source["path"] == "deploy/k8s/candidate-b"
    assert destination["server"] == STUDENT_SERVER
    assert destination["namespace"] == "tta-aiqa"
    assert "name" not in destination
    assert IN_CLUSTER_SERVER not in rendered
    assert "main" not in rendered
    assert "__TTA_AIQA_" not in rendered
    assert "automated" not in rendered
    assert "selfHeal" not in rendered
    assert "prune" not in rendered
    assert application["spec"]["syncPolicy"]["syncOptions"] == ["CreateNamespace=true"]


def test_shared_argo_student_destination_rejects_in_cluster_server() -> None:
    with pytest.raises(ValueError, match="in-cluster"):
        renderer.render(
            "c" * 40,
            "baseline",
            application_name=STUDENT_APP,
            destination_namespace="tta-aiqa",
            destination_server=IN_CLUSTER_SERVER,
        )


def test_render_requires_explicit_destination_outside_in_cluster() -> None:
    with pytest.raises(ValueError, match="destination"):
        renderer.render(
            "d" * 40,
            "baseline",
            application_name=STUDENT_APP,
            destination_namespace="tta-aiqa",
        )


def test_in_cluster_destination_requires_explicit_flag() -> None:
    rendered = renderer.render(
        "e" * 40,
        "baseline",
        application_name="tta-aiqa",
        destination_namespace="tta-aiqa",
        in_cluster=True,
    )
    application = yaml.safe_load(rendered)
    assert application["spec"]["destination"]["server"] == IN_CLUSTER_SERVER
    assert application["metadata"]["name"] == "tta-aiqa"


def test_in_cluster_flag_rejects_student_server() -> None:
    with pytest.raises(ValueError, match="in-cluster"):
        renderer.render(
            "f" * 40,
            "baseline",
            application_name=STUDENT_APP,
            destination_namespace="tta-aiqa",
            destination_server=STUDENT_SERVER,
            in_cluster=True,
        )


def test_destination_name_xor_server() -> None:
    rendered = renderer.render(
        "1" * 40,
        "rollback",
        application_name=STUDENT_APP,
        destination_namespace="tta-aiqa",
        destination_name="student-201",
    )
    destination = yaml.safe_load(rendered)["spec"]["destination"]
    assert destination["name"] == "student-201"
    assert "server" not in destination
    assert IN_CLUSTER_SERVER not in rendered

    with pytest.raises(ValueError, match="exactly one"):
        renderer.render(
            "1" * 40,
            "rollback",
            application_name=STUDENT_APP,
            destination_namespace="tta-aiqa",
            destination_server=STUDENT_SERVER,
            destination_name="student-201",
        )


@pytest.mark.parametrize(
    "revision",
    ["main", "feat/v2-monorepo", "ABCDEF", "a" * 39, "a" * 41],
)
def test_argocd_release_rejects_mutable_or_partial_revisions(revision: str) -> None:
    with pytest.raises(ValueError, match="40-character"):
        renderer.render(revision, "baseline", **_student_kwargs())


def test_argocd_release_rejects_unknown_overlay() -> None:
    with pytest.raises(ValueError, match="overlay"):
        renderer.render("b" * 40, "student-experiment", **_student_kwargs())
