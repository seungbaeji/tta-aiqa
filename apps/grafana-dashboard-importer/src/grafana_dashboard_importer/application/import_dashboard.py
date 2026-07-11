"""Bind one dashboard template and import it idempotently."""

from copy import deepcopy
from typing import Any

from grafana_dashboard_importer.domain import DashboardImport, ImportResult
from grafana_dashboard_importer.ports import DashboardGateway

DATASOURCE_PLACEHOLDERS = {
    "__AIQA_METRICS_UID__": "metrics",
    "__AIQA_LOGS_UID__": "logs",
    "__AIQA_TRACES_UID__": "traces",
}


class ImportDashboard:
    def __init__(self, gateway: DashboardGateway) -> None:
        self._gateway = gateway

    def execute(
        self,
        *,
        template: dict[str, Any],
        folder_uid: str,
        datasource_uids: dict[str, str],
    ) -> ImportResult:
        missing = set(DATASOURCE_PLACEHOLDERS.values()) - set(datasource_uids)
        if missing:
            raise ValueError(f"missing datasource bindings: {sorted(missing)}")
        for uid in datasource_uids.values():
            self._gateway.verify_datasource(uid)
        dashboard = _bind(deepcopy(template), datasource_uids)
        return self._gateway.import_dashboard(DashboardImport(dashboard, folder_uid))


def _bind(value: Any, datasource_uids: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _bind(item, datasource_uids) for key, item in value.items()}
    if isinstance(value, list):
        return [_bind(item, datasource_uids) for item in value]
    if isinstance(value, str) and value in DATASOURCE_PLACEHOLDERS:
        return datasource_uids[DATASOURCE_PLACEHOLDERS[value]]
    return value
