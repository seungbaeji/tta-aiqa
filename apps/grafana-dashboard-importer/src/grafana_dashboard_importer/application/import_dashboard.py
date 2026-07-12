"""Bind one dashboard template and import it idempotently."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from grafana_dashboard_importer.domain import (
    DashboardImport,
    DashboardTemplate,
    ImportResult,
)
from grafana_dashboard_importer.ports import DashboardGateway

DATASOURCE_PLACEHOLDERS = {
    "__AIQA_METRICS_UID__": "metrics",
    "__AIQA_LOGS_UID__": "logs",
    "__AIQA_TRACES_UID__": "traces",
}


def import_dashboard(
    *,
    gateway: DashboardGateway,
    template: DashboardTemplate,
    folder_uid: str,
    datasource_uids: Mapping[str, str],
) -> ImportResult:
    """Bind a validated template and import it through the configured gateway."""
    missing = set(DATASOURCE_PLACEHOLDERS.values()) - set(datasource_uids)
    if missing:
        raise ValueError(f"missing datasource bindings: {sorted(missing)}")
    for uid in datasource_uids.values():
        gateway.verify_datasource(uid)
    dashboard = _bind(deepcopy(dict(template.document)), datasource_uids)
    return gateway.import_dashboard(DashboardImport(dashboard, folder_uid))


def _bind(value: Any, datasource_uids: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _bind(item, datasource_uids) for key, item in value.items()}
    if isinstance(value, list):
        return [_bind(item, datasource_uids) for item in value]
    if isinstance(value, str) and value in DATASOURCE_PLACEHOLDERS:
        return datasource_uids[DATASOURCE_PLACEHOLDERS[value]]
    return value
