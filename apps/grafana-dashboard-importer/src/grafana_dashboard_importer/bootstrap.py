"""Composition root for the Grafana Cloud Dashboard Importer."""

from grafana_dashboard_importer.adapters import (
    GrafanaHttpGateway,
    load_dashboard_template,
)
from grafana_dashboard_importer.application import ImportDashboard
from grafana_dashboard_importer.domain import ImportResult
from grafana_dashboard_importer.settings import GrafanaDashboardSettings


def bootstrap(**overrides: object) -> ImportResult:
    settings = GrafanaDashboardSettings(**overrides)
    gateway = GrafanaHttpGateway(
        base_url=str(settings.url),
        token=settings.dashboard_token.get_secret_value(),
    )
    return ImportDashboard(gateway).execute(
        template=load_dashboard_template(settings.dashboard_path),
        folder_uid=settings.folder_uid,
        datasource_uids={
            "metrics": settings.metrics_datasource_uid,
            "logs": settings.logs_datasource_uid,
            "traces": settings.traces_datasource_uid,
        },
    )
