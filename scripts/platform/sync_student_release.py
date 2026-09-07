"""Sync an already-registered student Argo CD Application to Candidate B."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.platform.render_argocd_application import IN_CLUSTER_SERVER
from scripts.platform.verify_target_release import RELEASES

ROOT = Path(__file__).resolve().parents[2]
ARGOCD_NAMESPACE = "argocd"
CANDIDATE_B_OVERLAY = "candidate-b"
CANDIDATE_B_PATH = f"deploy/k8s/{CANDIDATE_B_OVERLAY}"
CANDIDATE_B_VERSION = RELEASES["candidate-b"].version
FORBIDDEN_AUTOMATED_TOKENS = ("automated", "selfHeal", "prune")


class SyncBlocked(RuntimeError):
    """Refuse a cluster change and keep the student path fail-closed."""


def _command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    """Run one kubectl command without raising on a non-zero exit."""
    return subprocess.run(
        arguments,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def require_target_context(target_context: str | None) -> str:
    """Fail before any cluster query unless TARGET_CONTEXT is set and active."""
    if not target_context:
        raise SyncBlocked("TARGET_CONTEXT is required; refusing to change a cluster.")
    try:
        result = _command(("kubectl", "config", "current-context"))
    except OSError as error:
        raise SyncBlocked(
            "kubectl is unavailable; refusing to change a cluster."
        ) from error
    if result.returncode != 0:
        raise SyncBlocked(
            "Unable to read the current Kubernetes context; refusing to continue."
        )
    current = result.stdout.strip()
    if not current:
        raise SyncBlocked(
            "Unable to read the current Kubernetes context; refusing to continue."
        )
    if current != target_context:
        raise SyncBlocked(
            f"Context mismatch: expected {target_context}, got {current}"
        )
    return current


def load_existing_application(context: str, name: str) -> dict[str, Any]:
    """Read one Application. Never create the resource when it is missing."""
    result = _command(
        (
            "kubectl",
            "--context",
            context,
            "-n",
            ARGOCD_NAMESPACE,
            "get",
            "application",
            name,
            "-o",
            "json",
        )
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SyncBlocked(
            f"Application {name!r} was not found; refusing to create an "
            "Application"
            + (f": {detail}" if detail else "")
        )
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SyncBlocked(
            "existing Application document was not valid JSON; refusing to patch"
        ) from error
    if not isinstance(document, dict) or document.get("kind") != "Application":
        raise SyncBlocked(
            f"resource {name!r} is not an Argo CD Application; refusing to patch"
        )
    return document


def assert_safe_student_application(document: dict[str, Any]) -> None:
    """Reject in-cluster destinations and automated prune/selfHeal."""
    spec = document.get("spec")
    if not isinstance(spec, dict):
        raise SyncBlocked("Application spec is missing; refusing to patch")
    destination = spec.get("destination")
    if not isinstance(destination, dict):
        raise SyncBlocked("Application destination is missing; refusing to patch")
    server = str(destination.get("server") or "")
    name = str(destination.get("name") or "")
    if IN_CLUSTER_SERVER in server:
        raise SyncBlocked(
            "student VM destination must not be kubernetes.default.svc"
        )
    if not server and not name:
        raise SyncBlocked("Application destination is missing; refusing to patch")
    sync_policy = spec.get("syncPolicy") or {}
    serialized_policy = json.dumps(sync_policy)
    if any(token in serialized_policy for token in FORBIDDEN_AUTOMATED_TOKENS):
        raise SyncBlocked(
            "refusing to sync an Application with automated prune/selfHeal"
        )


def patch_existing_application_to_candidate_b(context: str, name: str) -> None:
    """Point the existing Application at Candidate B and request a manual sync."""
    payload = json.dumps(
        {
            "spec": {"source": {"path": CANDIDATE_B_PATH}},
            "operation": {
                "initiatedBy": {"username": "student"},
                "sync": {"syncStrategy": {"hook": {}}},
            },
        }
    )
    result = _command(
        (
            "kubectl",
            "--context",
            context,
            "-n",
            ARGOCD_NAMESPACE,
            "patch",
            "application",
            name,
            "--type",
            "merge",
            "-p",
            payload,
        )
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SyncBlocked(
            detail or "Application patch/sync to Candidate B failed"
        )


def sync_existing_release(
    *,
    application_name: str,
    target_context: str | None,
) -> dict[str, str]:
    """Switch one already-registered Application to the Candidate B overlay."""
    name = application_name.strip()
    if not name:
        raise SyncBlocked(
            "already-registered Application name is required; refusing to create"
        )
    context = require_target_context(target_context)
    document = load_existing_application(context, name)
    assert_safe_student_application(document)
    patch_existing_application_to_candidate_b(context, name)
    return {
        "result": "synced",
        "application": name,
        "path": CANDIDATE_B_PATH,
        "expected_version": CANDIDATE_B_VERSION,
        "context": context,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--application-name",
        required=True,
        help="already-registered Argo CD Application; this script never creates one",
    )
    parser.add_argument(
        "--overlay",
        choices=(CANDIDATE_B_OVERLAY,),
        default=CANDIDATE_B_OVERLAY,
        help="student overlay switch is limited to approved Candidate B",
    )
    return parser


def main() -> int:
    """Fail closed, sync an existing Application, and never create one."""
    args = _parser().parse_args()
    try:
        result = sync_existing_release(
            application_name=args.application_name,
            target_context=os.environ.get("TARGET_CONTEXT"),
        )
    except SyncBlocked as error:
        print(f"result=BLOCKED reason={error}", file=sys.stderr)
        return 1
    print(
        "synced existing Application "
        f"{result['application']!r} to {result['path']}"
    )
    print(f"expected /v1/model version: {result['expected_version']}")
    print(
        "GET ${AIQA_RISK_API_URL}/v1/model to confirm. "
        "If that URL is missing, record operational_deployment_scope="
        "target_pending and do not invent identity."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
