"""Import one bound dashboard template through an idempotent gateway."""

from grafana_dashboard_importer.domain import (
    DashboardDatasourceBindings,
    DashboardImport,
    DashboardTemplate,
    ImportResult,
    bind_dashboard_template,
)
from grafana_dashboard_importer.ports import DashboardGateway


def import_dashboard(
    *,
    gateway: DashboardGateway,
    template: DashboardTemplate,
    folder_uid: str,
    datasource_bindings: DashboardDatasourceBindings,
) -> ImportResult:
    """Bind a validated template and import it through the configured gateway."""
    for uid in datasource_bindings.uids:
        gateway.verify_datasource(uid)
    dashboard = bind_dashboard_template(template, datasource_bindings)
    return gateway.import_dashboard(DashboardImport(dashboard, folder_uid))
