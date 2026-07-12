"""Grafana Dashboard Importer application and domain behavior tests."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from grafana_dashboard_importer.application import import_dashboard
from grafana_dashboard_importer.domain import (
    DashboardDatasourceBindings,
    DashboardImport,
    DashboardTemplate,
    ImportResult,
    bind_dashboard_template,
)


def template() -> DashboardTemplate:
    """Return a nested template that exercises every declared placeholder."""
    return DashboardTemplate(
        uid="aiqa-quality",
        title="AI Quality",
        document={
            "uid": "aiqa-quality",
            "title": "AI Quality",
            "panels": [
                {"datasource": {"uid": "__AIQA_METRICS_UID__"}},
                {"datasource": {"uid": "__AIQA_LOGS_UID__"}},
                {"datasource": {"uid": "__AIQA_TRACES_UID__"}},
            ],
            "literal": "unchanged",
        },
    )


def bindings() -> DashboardDatasourceBindings:
    """Return one student's validated datasource UID set."""
    return DashboardDatasourceBindings(
        metrics_uid="prometheus-uid",
        logs_uid="loki-uid",
        traces_uid="tempo-uid",
    )


@dataclass
class DashboardGatewaySpy:
    """Capture the ordered application calls without invoking Grafana HTTP."""

    events: list[str] = field(default_factory=list)
    imported: DashboardImport | None = None

    def verify_datasource(self, uid: str) -> None:
        """Record that the use case verified one bound datasource first."""
        self.events.append(f"verify:{uid}")

    def import_dashboard(self, request: DashboardImport) -> ImportResult:
        """Capture the final request after datasource verification completes."""
        self.events.append("import")
        self.imported = request
        return ImportResult(
            uid=request.dashboard["uid"],
            url="https://grafana.example.test/d/aiqa-quality",
            status="success",
        )


def test_binding_replaces_declared_values_without_mutating_the_template() -> None:
    """Datasource binding returns a new structured dashboard document."""
    configured_template = template()

    dashboard = bind_dashboard_template(configured_template, bindings())

    panel_uids = [panel["datasource"]["uid"] for panel in dashboard["panels"]]
    assert panel_uids == ["prometheus-uid", "loki-uid", "tempo-uid"]
    assert dashboard["literal"] == "unchanged"
    assert configured_template.document["panels"][0]["datasource"]["uid"] == (
        "__AIQA_METRICS_UID__"
    )


def test_import_use_case_verifies_datasources_before_stable_uid_import() -> None:
    """The application orchestrates domain binding and only the outbound gateway."""
    gateway = DashboardGatewaySpy()

    result = import_dashboard(
        gateway=gateway,
        template=template(),
        folder_uid="course",
        datasource_bindings=bindings(),
    )

    assert result.uid == "aiqa-quality"
    assert gateway.events == [
        "verify:prometheus-uid",
        "verify:loki-uid",
        "verify:tempo-uid",
        "import",
    ]
    assert gateway.imported is not None
    assert gateway.imported.folder_uid == "course"


def test_bindings_reject_empty_or_untrimmed_datasource_uids() -> None:
    """Datasource binding inputs must be safe to pass to Grafana API paths."""
    with pytest.raises(ValueError, match="non-empty and trimmed"):
        DashboardDatasourceBindings(
            metrics_uid="prometheus-uid",
            logs_uid=" ",
            traces_uid="tempo-uid",
        )
