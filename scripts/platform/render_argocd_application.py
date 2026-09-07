"""Render the course Argo CD Application with an immutable Git revision."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "deploy/argocd/tta-aiqa.template.yaml"
DEFAULT_OUTPUT = ROOT / "artifacts/deploy/argocd-tta-aiqa.yaml"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_OVERLAYS = {"baseline", "baseline-observed", "candidate-b", "rollback"}
IN_CLUSTER_SERVER = "https://kubernetes.default.svc"
FORBIDDEN_SYNC_TOKENS = ("automated", "selfHeal", "prune:")


def render(
    revision: str,
    overlay: str,
    *,
    application_name: str,
    destination_namespace: str,
    destination_server: str | None = None,
    destination_name: str | None = None,
    in_cluster: bool = False,
) -> str:
    """Bind a reviewed commit, overlay, and explicit Argo destination.

    Shared Argo/student targets must pass ``destination_server`` or
    ``destination_name``. In-cluster ``kubernetes.default.svc`` is emitted only
    when ``in_cluster`` is true. Automated prune/selfHeal is never rendered.
    """

    if not COMMIT_PATTERN.fullmatch(revision):
        raise ValueError("revision must be a full 40-character lowercase Git commit")
    if overlay not in ALLOWED_OVERLAYS:
        allowed = ", ".join(sorted(ALLOWED_OVERLAYS))
        raise ValueError(f"overlay must be one of: {allowed}")
    if not application_name.strip():
        raise ValueError("application name is required")
    if not destination_namespace.strip():
        raise ValueError("destination namespace is required")

    dest_ref = _destination_ref(
        destination_server=destination_server,
        destination_name=destination_name,
        in_cluster=in_cluster,
    )

    source = TEMPLATE.read_text(encoding="utf-8")
    rendered = source.replace("__TTA_AIQA_REVISION__", revision)
    rendered = rendered.replace("__TTA_AIQA_OVERLAY__", overlay)
    rendered = rendered.replace("__TTA_AIQA_APP_NAME__", application_name.strip())
    rendered = rendered.replace(
        "__TTA_AIQA_DEST_NAMESPACE__", destination_namespace.strip()
    )
    rendered = rendered.replace("__TTA_AIQA_DEST_REF__", dest_ref)
    if "__TTA_AIQA_" in rendered:
        raise ValueError("not all Argo CD template placeholders were replaced")
    _assert_safe_rendered(
        rendered,
        revision=revision,
        overlay=overlay,
        application_name=application_name.strip(),
        destination_namespace=destination_namespace.strip(),
        in_cluster=in_cluster,
    )
    return rendered


def _destination_ref(
    *,
    destination_server: str | None,
    destination_name: str | None,
    in_cluster: bool,
) -> str:
    server = (destination_server or "").strip() or None
    name = (destination_name or "").strip() or None
    if in_cluster:
        if server or name:
            raise ValueError(
                "in-cluster destination cannot combine with destination server or name"
            )
        return f"server: {IN_CLUSTER_SERVER}"
    if server == IN_CLUSTER_SERVER:
        raise ValueError(
            "in-cluster kubernetes.default.svc requires explicit in_cluster=True"
        )
    if server and name:
        raise ValueError("provide exactly one of destination server or name")
    if not server and not name:
        raise ValueError("destination server or name is required")
    if server:
        return f"server: {server}"
    return f"name: {name}"


def _assert_safe_rendered(
    rendered: str,
    *,
    revision: str,
    overlay: str,
    application_name: str,
    destination_namespace: str,
    in_cluster: bool,
) -> None:
    """Reject rendered Applications that would silently target the Argo cluster."""

    if application_name not in rendered:
        raise ValueError("rendered application name does not match the caller value")
    if f"targetRevision: {revision}" not in rendered:
        raise ValueError("rendered targetRevision does not match the immutable SHA")
    expected_path = f"deploy/k8s/{overlay}"
    if expected_path not in rendered:
        raise ValueError("rendered path does not match the selected overlay")
    if f"namespace: {destination_namespace}" not in rendered:
        raise ValueError("rendered destination namespace does not match")
    if "CreateNamespace=true" not in rendered:
        raise ValueError("rendered syncPolicy must keep CreateNamespace")
    if any(token in rendered for token in FORBIDDEN_SYNC_TOKENS):
        raise ValueError("rendered syncPolicy must not enable automated prune/selfHeal")
    if in_cluster:
        if f"server: {IN_CLUSTER_SERVER}" not in rendered:
            raise ValueError("in-cluster render must set kubernetes.default.svc")
        return
    if IN_CLUSTER_SERVER in rendered:
        raise ValueError(
            "student/shared Argo destination must not use kubernetes.default.svc"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--overlay", choices=sorted(ALLOWED_OVERLAYS), required=True)
    parser.add_argument("--application-name", required=True)
    parser.add_argument("--destination-namespace", required=True)
    parser.add_argument("--destination-server")
    parser.add_argument("--destination-name")
    parser.add_argument(
        "--in-cluster",
        action="store_true",
        help="explicit local/in-cluster destination (kubernetes.default.svc)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rendered = render(
        args.revision,
        args.overlay,
        application_name=args.application_name,
        destination_namespace=args.destination_namespace,
        destination_server=args.destination_server,
        destination_name=args.destination_name,
        in_cluster=args.in_cluster,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"rendered immutable Argo CD application: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
