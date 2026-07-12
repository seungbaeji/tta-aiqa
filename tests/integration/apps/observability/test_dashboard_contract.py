"""Dashboard queries must follow the runtime telemetry contract."""

import json
from pathlib import Path

from risk_api.config import load_api_config


def test_dashboard_uses_declared_metrics_and_all_three_datasources() -> None:
    dashboard = json.loads(
        Path("deploy/grafana-cloud/dashboards/ai-quality.json").read_text()
    )
    config = load_api_config(Path("configs/serving/api.yaml"))
    queries = " ".join(
        str(target)
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    )
    datasource_uids = {
        panel["datasource"]["uid"] for panel in dashboard["panels"]
    }

    for metric_name in config.observability.metrics.model_dump().values():
        assert metric_name in queries
    assert datasource_uids == {
        "__AIQA_METRICS_UID__",
        "__AIQA_LOGS_UID__",
        "__AIQA_TRACES_UID__",
    }
    assert dashboard["uid"] == "tta-aiqa-quality"
