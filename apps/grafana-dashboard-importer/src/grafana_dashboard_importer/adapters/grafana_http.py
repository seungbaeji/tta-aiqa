"""Grafana Cloud Dashboard HTTP API adapter."""

from urllib.parse import urljoin

import requests

from grafana_dashboard_importer.domain import DashboardImport, ImportResult


class GrafanaHttpGateway:
    """Call the Grafana dashboard API with a dashboard-scoped credential."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        session: requests.Session | None = None,
    ) -> None:
        """Configure the API base URL and reusable authenticated HTTP session."""
        self._base_url = base_url.rstrip("/") + "/"
        self._session = session or requests.Session()
        self._session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def verify_datasource(self, uid: str) -> None:
        """Fail unless Grafana exposes the datasource UID to the current token."""
        response = self._session.get(
            urljoin(self._base_url, f"api/datasources/uid/{uid}"), timeout=15
        )
        response.raise_for_status()

    def import_dashboard(self, request: DashboardImport) -> ImportResult:
        """Create or overwrite the fixed-UID dashboard and return Grafana's result."""
        response = self._session.post(
            urljoin(self._base_url, "api/dashboards/db"),
            json={
                "dashboard": request.dashboard,
                "folderUid": request.folder_uid,
                "overwrite": True,
                "message": "Managed by tta-aiqa dashboard importer",
            },
            timeout=30,
        )
        response.raise_for_status()
        document = response.json()
        return ImportResult(
            uid=str(document["uid"]),
            url=urljoin(self._base_url, str(document["url"]).lstrip("/")),
            status=str(document["status"]),
        )
