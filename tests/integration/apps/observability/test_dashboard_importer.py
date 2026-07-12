"""Dashboard binding and idempotent API payload tests."""

from pathlib import Path

from grafana_dashboard_importer.adapters import load_dashboard_template
from grafana_dashboard_importer.application import import_dashboard
from grafana_dashboard_importer.domain import DashboardImport, ImportResult


class FakeGateway:
    def __init__(self) -> None:
        self.verified: list[str] = []
        self.imports: list[DashboardImport] = []

    def verify_datasource(self, uid: str) -> None:
        self.verified.append(uid)

    def import_dashboard(self, request: DashboardImport) -> ImportResult:
        self.imports.append(request)
        return ImportResult(request.dashboard["uid"], "/d/tta-aiqa-quality", "success")


def test_importer_binds_datasources_and_keeps_stable_dashboard_uid() -> None:
    template = load_dashboard_template(
        Path("deploy/grafana-cloud/dashboards/ai-quality.json")
    )
    gateway = FakeGateway()

    first = import_dashboard(
        gateway=gateway,
        template=template,
        folder_uid="course",
        datasource_uids={"metrics": "prom", "logs": "loki", "traces": "tempo"},
    )
    second = import_dashboard(
        gateway=gateway,
        template=template,
        folder_uid="course",
        datasource_uids={"metrics": "prom", "logs": "loki", "traces": "tempo"},
    )

    assert first.uid == second.uid == "tta-aiqa-quality"
    assert len(gateway.imports) == 2
    serialized = str(gateway.imports[0].dashboard)
    assert "__AIQA_" not in serialized
    assert {"prom", "loki", "tempo"} <= set(gateway.verified)
