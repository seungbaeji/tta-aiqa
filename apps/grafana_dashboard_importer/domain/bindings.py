"""Dashboard datasource binding values and pure transformation rules."""

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from grafana_dashboard_importer.domain.dashboard import DashboardTemplate


class DashboardDatasource(StrEnum):
    """Datasource roles required by the course dashboard template."""

    METRICS = "metrics"
    LOGS = "logs"
    TRACES = "traces"


DASHBOARD_DATASOURCE_PLACEHOLDERS = MappingProxyType(
    {
        "__AIQA_METRICS_UID__": DashboardDatasource.METRICS,
        "__AIQA_LOGS_UID__": DashboardDatasource.LOGS,
        "__AIQA_TRACES_UID__": DashboardDatasource.TRACES,
    }
)


@dataclass(frozen=True)
class DashboardDatasourceBindings:
    """Validated Grafana datasource UIDs for one student's dashboard import."""

    metrics_uid: str
    logs_uid: str
    traces_uid: str

    def __post_init__(self) -> None:
        if any(not uid or uid.strip() != uid for uid in self.uids):
            raise ValueError("dashboard datasource UIDs must be non-empty and trimmed")

    @property
    def uids(self) -> tuple[str, str, str]:
        """Return datasource UIDs in the stable verification order."""
        return (self.metrics_uid, self.logs_uid, self.traces_uid)

    def replace_placeholder(self, value: str) -> str:
        """Replace one declared template placeholder or preserve an ordinary value."""
        datasource = DASHBOARD_DATASOURCE_PLACEHOLDERS.get(value)
        if datasource is DashboardDatasource.METRICS:
            return self.metrics_uid
        if datasource is DashboardDatasource.LOGS:
            return self.logs_uid
        if datasource is DashboardDatasource.TRACES:
            return self.traces_uid
        return value


def bind_dashboard_template(
    template: DashboardTemplate,
    bindings: DashboardDatasourceBindings,
) -> dict[str, Any]:
    """Return a deep-copied dashboard document with declared datasource UIDs bound."""
    document: dict[str, Any] = deepcopy(dict(template.document))
    pending: list[dict[str, Any] | list[Any]] = [document]
    while pending:
        container = pending.pop()
        if isinstance(container, dict):
            for key, value in container.items():
                if isinstance(value, str):
                    container[key] = bindings.replace_placeholder(value)
                elif isinstance(value, (dict, list)):
                    pending.append(value)
        else:
            for index, value in enumerate(container):
                if isinstance(value, str):
                    container[index] = bindings.replace_placeholder(value)
                elif isinstance(value, (dict, list)):
                    pending.append(value)
    return document
