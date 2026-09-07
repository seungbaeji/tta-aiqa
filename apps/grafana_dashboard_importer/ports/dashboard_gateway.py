"""Outbound dashboard management port."""

from typing import Protocol

from grafana_dashboard_importer.domain import DashboardImport, ImportResult


class DashboardGateway(Protocol):
    """Verify datasource access and import one bound dashboard document."""

    def verify_datasource(self, uid: str) -> None:
        """Fail unless the configured Grafana credential can read this datasource."""
        ...

    def import_dashboard(self, request: DashboardImport) -> ImportResult:
        """Create or replace a dashboard using its stable dashboard UID."""
        ...
