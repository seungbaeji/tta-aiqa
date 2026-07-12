"""Composition root for the Grafana Cloud Dashboard Importer."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from aiqa_observability import Telemetry, create_telemetry, load_telemetry_policy

from grafana_dashboard_importer.adapters import (
    GrafanaHttpGateway,
    load_dashboard_template,
)
from grafana_dashboard_importer.application import import_dashboard
from grafana_dashboard_importer.domain import (
    DashboardDatasourceBindings,
    DashboardTemplate,
    ImportResult,
)
from grafana_dashboard_importer.settings import GrafanaDashboardSettings


@dataclass(frozen=True)
class DashboardRuntime:
    """Bound dashboard operation and process resources for the CLI adapter."""

    template: DashboardTemplate
    folder_uid: str
    run_import: Callable[[], ImportResult]
    telemetry: Telemetry


def bootstrap(**overrides: object) -> DashboardRuntime:
    """Assemble concrete Grafana Cloud adapters for one process."""
    settings = GrafanaDashboardSettings(**overrides)
    gateway = GrafanaHttpGateway(
        base_url=str(settings.url),
        token=settings.dashboard_token.get_secret_value(),
    )
    template = load_dashboard_template(settings.dashboard_path)
    datasource_bindings = DashboardDatasourceBindings(
        metrics_uid=settings.metrics_datasource_uid,
        logs_uid=settings.logs_datasource_uid,
        traces_uid=settings.traces_datasource_uid,
    )

    return DashboardRuntime(
        template=template,
        folder_uid=settings.folder_uid,
        run_import=partial(
            import_dashboard,
            gateway=gateway,
            template=template,
            folder_uid=settings.folder_uid,
            datasource_bindings=datasource_bindings,
        ),
        telemetry=create_telemetry(
            service_name="grafana-dashboard-importer",
            environment=settings.environment,
            policy=load_telemetry_policy(settings.telemetry_config_path),
            otlp_endpoint=(
                str(settings.otlp_endpoint) if settings.otlp_endpoint else None
            ),
        ),
    )
