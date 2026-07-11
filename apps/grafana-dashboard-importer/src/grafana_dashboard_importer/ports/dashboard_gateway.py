"""Outbound dashboard management port."""

from typing import Protocol

from grafana_dashboard_importer.domain import DashboardImport, ImportResult


class DashboardGateway(Protocol):
    def verify_datasource(self, uid: str) -> None: ...

    def import_dashboard(self, request: DashboardImport) -> ImportResult: ...
