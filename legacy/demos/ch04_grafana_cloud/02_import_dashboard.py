"""Import the chapter 4 dashboard JSON into Grafana Cloud.

Credentials are read only from environment variables. Do not write tokens into
this script, config files, shell history, or course documents.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from env_loader import load_root_env

DEFAULT_DASHBOARD_PATHS = (
    Path("artifacts/grafana/ai_quality_overview_dashboard.json"),
    Path("artifacts/grafana/ai_quality_details_dashboard.json"),
)
DEFAULT_FOLDER_UID = "ai-quality"
DEFAULT_FOLDER_TITLE = "AI Quality"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def _json_request(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return error.code, body


def _dashboard_app_payload(
    dashboard: dict[str, Any],
    dashboard_uid: str,
    folder_uid: str | None,
) -> dict[str, Any]:
    annotations: dict[str, str] = {}
    if folder_uid:
        annotations["grafana.app/folder"] = folder_uid

    metadata: dict[str, Any] = {"name": dashboard_uid}
    if annotations:
        metadata["annotations"] = annotations

    dashboard = {**dashboard, "uid": dashboard_uid, "version": 0}
    return {
        "metadata": metadata,
        "spec": dashboard,
    }


def _legacy_dashboard_payload(
    dashboard: dict[str, Any],
    dashboard_uid: str,
    folder_uid: str | None,
) -> dict[str, Any]:
    dashboard = {**dashboard, "id": None, "uid": dashboard_uid}
    payload: dict[str, Any] = {
        "dashboard": dashboard,
        "overwrite": True,
        "message": "Import AI Quality training dashboard",
    }
    if folder_uid:
        payload["folderUid"] = folder_uid
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import chapter 4 Grafana dashboard JSON files to Grafana Cloud."
        ),
    )
    parser.add_argument(
        "--dashboard-json",
        type=Path,
        action="append",
        help=(
            "Dashboard JSON artifact path. Repeat to import multiple files. "
            "Defaults to overview and details dashboards."
        ),
    )
    parser.add_argument(
        "--namespace",
        default=os.environ.get("GRAFANA_DASHBOARD_NAMESPACE", "default"),
        help="Grafana API namespace. Defaults to default.",
    )
    parser.add_argument(
        "--dashboard-uid",
        help="Dashboard uid/name. Only use with one dashboard JSON.",
    )
    parser.add_argument(
        "--folder-uid",
        default=os.environ.get("GRAFANA_FOLDER_UID") or DEFAULT_FOLDER_UID,
        help="Grafana folder uid. Defaults to ai-quality.",
    )
    parser.add_argument(
        "--folder-title",
        default=os.environ.get("GRAFANA_FOLDER_TITLE") or DEFAULT_FOLDER_TITLE,
        help="Grafana folder title. Defaults to AI Quality.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the endpoint and payload summary without sending.",
    )
    return parser.parse_args()


def main() -> None:
    load_root_env()
    args = parse_args()
    grafana_url = os.environ.get("GRAFANA_CLOUD_URL", "").rstrip("/")
    if not grafana_url and not args.dry_run:
        raise SystemExit("missing required environment variable: GRAFANA_CLOUD_URL")

    token_env_name = "GRAFANA_DASHBOARD_TOKEN"
    token = os.environ.get(token_env_name, "")
    if not token and not args.dry_run:
        raise SystemExit(
            "missing required environment variable: GRAFANA_DASHBOARD_TOKEN"
        )

    dashboard_paths = tuple(args.dashboard_json or DEFAULT_DASHBOARD_PATHS)
    env_dashboard_uid = os.environ.get("GRAFANA_DASHBOARD_UID")
    dashboard_uid_override = args.dashboard_uid
    if dashboard_uid_override and len(dashboard_paths) > 1:
        raise SystemExit("--dashboard-uid can only be used with one dashboard JSON")

    folder_uid = args.folder_uid or None
    if folder_uid and args.dry_run:
        print("dry_run=True")
        print(f"folder_uid={folder_uid}")
        print(f"folder_title={args.folder_title}")
    if folder_uid and not args.dry_run:
        folder_uid = ensure_folder(
            grafana_url=grafana_url,
            token=token,
            namespace=args.namespace,
            folder_uid=folder_uid,
            folder_title=args.folder_title,
        )

    imported_count = 0
    for dashboard_path in dashboard_paths:
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        dashboard_uid = dashboard_uid_override or (
            env_dashboard_uid if len(dashboard_paths) == 1 else None
        ) or str(
            dashboard.get("uid", "ai-quality-overview")
        )
        import_dashboard(
            grafana_url=grafana_url,
            token=token,
            token_env_name=token_env_name,
            dashboard=dashboard,
            dashboard_path=dashboard_path,
            dashboard_uid=dashboard_uid,
            namespace=args.namespace,
            folder_uid=folder_uid,
            dry_run=args.dry_run,
        )
        imported_count += 1

    if not args.dry_run:
        print(f"dashboard_import_count={imported_count}")
        print("dashboard_import_result=ok")


def import_dashboard(
    *,
    grafana_url: str,
    token: str,
    token_env_name: str,
    dashboard: dict[str, Any],
    dashboard_path: Path,
    dashboard_uid: str,
    namespace: str,
    folder_uid: str | None,
    dry_run: bool,
) -> None:
    """Import one dashboard JSON file."""
    app_payload = _dashboard_app_payload(
        dashboard=dashboard,
        dashboard_uid=dashboard_uid,
        folder_uid=folder_uid,
    )
    app_endpoint = (
        f"{grafana_url}/apis/dashboard.grafana.app/v1/"
        f"namespaces/{namespace}/dashboards"
    )
    legacy_endpoint = f"{grafana_url}/api/dashboards/db"

    if dry_run:
        print("dry_run=True")
        print(f"dashboard_json={dashboard_path}")
        print(f"app_endpoint={app_endpoint or '<GRAFANA_CLOUD_URL not set>'}")
        print(f"legacy_endpoint={legacy_endpoint or '<GRAFANA_CLOUD_URL not set>'}")
        print(f"dashboard_uid={dashboard_uid}")
        print(f"folder_uid={folder_uid or '-'}")
        print(f"token_env={token_env_name}")
        print(f"panel_count={len(dashboard.get('panels', []))}")
        return

    status, body = _json_request(
        method="POST",
        url=app_endpoint,
        token=token,
        payload=app_payload,
    )
    if status == 409:
        update_endpoint = f"{app_endpoint}/{dashboard_uid}"
        status, body = _json_request(
            method="PUT",
            url=update_endpoint,
            token=token,
            payload=app_payload,
        )
    api_mode = "dashboard.grafana.app"

    if status in {403, 404} and (
        "invalid namespace" in body.lower() or "not found" in body.lower()
    ):
        status, body = _json_request(
            method="POST",
            url=legacy_endpoint,
            token=token,
            payload=_legacy_dashboard_payload(
                dashboard=dashboard,
                dashboard_uid=dashboard_uid,
                folder_uid=folder_uid,
            ),
        )
        api_mode = "legacy-dashboard-api"

    if status not in {200, 201}:
        print(body, file=sys.stderr)
        raise SystemExit(f"dashboard import failed: HTTP {status}")

    print(f"dashboard_import_status={status}")
    print(f"dashboard_import_api={api_mode}")
    print(f"dashboard_import_token_env={token_env_name}")
    print(f"dashboard_uid={dashboard_uid}")
    print(f"dashboard_folder_uid={folder_uid or '-'}")


def ensure_folder(
    *,
    grafana_url: str,
    token: str,
    namespace: str,
    folder_uid: str,
    folder_title: str,
) -> str:
    """Ensure the target Grafana folder exists and return its uid."""
    app_base = (
        f"{grafana_url}/apis/folder.grafana.app/v1/"
        f"namespaces/{namespace}/folders"
    )
    status, body = _json_request(
        method="GET",
        url=f"{app_base}/{folder_uid}",
        token=token,
    )
    if status == 200:
        print(f"dashboard_folder_uid={folder_uid}")
        print("dashboard_folder_api=folder.grafana.app")
        print("dashboard_folder_result=exists")
        return folder_uid

    if status == 404:
        status, body = _json_request(
            method="POST",
            url=app_base,
            token=token,
            payload={
                "metadata": {"name": folder_uid},
                "spec": {"title": folder_title},
            },
        )
        if status in {200, 201, 409}:
            print(f"dashboard_folder_uid={folder_uid}")
            print("dashboard_folder_api=folder.grafana.app")
            print(
                "dashboard_folder_result="
                + ("exists" if status == 409 else "created")
            )
            return folder_uid

    if status in {403, 404} and (
        "invalid namespace" in body.lower() or "not found" in body.lower()
    ):
        return ensure_legacy_folder(
            grafana_url=grafana_url,
            token=token,
            folder_uid=folder_uid,
            folder_title=folder_title,
        )

    print(body, file=sys.stderr)
    raise SystemExit(f"folder ensure failed: HTTP {status}")


def ensure_legacy_folder(
    *,
    grafana_url: str,
    token: str,
    folder_uid: str,
    folder_title: str,
) -> str:
    """Ensure the target folder exists through the legacy Folder API."""
    status, body = _json_request(
        method="GET",
        url=f"{grafana_url}/api/folders/{folder_uid}",
        token=token,
    )
    if status == 200:
        print(f"dashboard_folder_uid={folder_uid}")
        print("dashboard_folder_api=legacy-folder-api")
        print("dashboard_folder_result=exists")
        return folder_uid

    if status == 404:
        status, body = _json_request(
            method="POST",
            url=f"{grafana_url}/api/folders",
            token=token,
            payload={"uid": folder_uid, "title": folder_title},
        )
        if status in {200, 201, 409}:
            print(f"dashboard_folder_uid={folder_uid}")
            print("dashboard_folder_api=legacy-folder-api")
            print(
                "dashboard_folder_result="
                + ("exists" if status == 409 else "created")
            )
            return folder_uid

    print(body, file=sys.stderr)
    raise SystemExit(f"folder ensure failed: HTTP {status}")


if __name__ == "__main__":
    main()
