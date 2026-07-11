"""Dashboard queries must follow the runtime telemetry contract."""

import json
from pathlib import Path

from aiqa_observability.adapters import load_telemetry_contract


def test_dashboard_uses_declared_metrics_and_all_three_datasources() -> None:
    dashboard = json.loads(
        Path("deploy/grafana-cloud/dashboards/ai-quality.json").read_text()
    )
    contract = load_telemetry_contract(Path("configs/observability/telemetry.yaml"))
    queries = " ".join(
        str(target)
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    )
    datasource_uids = {
        panel["datasource"]["uid"] for panel in dashboard["panels"]
    }

    for metric_name in vars(contract.metrics).values():
        assert metric_name in queries
    assert datasource_uids == {
        "__AIQA_METRICS_UID__",
        "__AIQA_LOGS_UID__",
        "__AIQA_TRACES_UID__",
    }
    assert dashboard["uid"] == "tta-aiqa-quality"
