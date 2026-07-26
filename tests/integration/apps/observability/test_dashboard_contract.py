"""Dashboard queries must follow the runtime telemetry contract."""

import json
from pathlib import Path

from risk_api.adapters.config import load_api_config


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
    request_queries = [
        target["expr"]
        for panel in dashboard["panels"][:3]
        for target in panel.get("targets", [])
    ]
    assert all('route="/v1/predict"' in query for query in request_queries)
    assert datasource_uids == {
        "__AIQA_METRICS_UID__",
        "__AIQA_LOGS_UID__",
        "__AIQA_TRACES_UID__",
    }
    assert dashboard["uid"] == "tta-aiqa-quality"


def test_dashboard_filters_and_names_every_metric_series_by_bounded_scenario() -> None:
    dashboard = json.loads(
        Path("deploy/grafana-cloud/dashboards/ai-quality.json").read_text()
    )
    config = load_api_config(Path("configs/serving/api.yaml"))
    variables = {
        variable["name"]: variable for variable in dashboard["templating"]["list"]
    }
    scenario = variables["scenario"]
    metric_targets = [
        target
        for panel in dashboard["panels"]
        if panel["datasource"]["type"] == "prometheus"
        for target in panel.get("targets", [])
    ]

    assert scenario["type"] == "custom"
    assert scenario["includeAll"] is True
    assert scenario["allValue"] == ".*"
    assert set(scenario["query"].split(",")) == set(
        config.observability.allowed_scenarios
    )
    assert metric_targets
    assert all(
        'scenario=~"${scenario:regex}"' in target["expr"]
        for target in metric_targets
    )
    assert all("scenario" in target["expr"] for target in metric_targets)
    assert all("{{scenario}}" in target["legendFormat"] for target in metric_targets)
    logs_target = next(
        panel["targets"][0]
        for panel in dashboard["panels"]
        if panel["datasource"]["type"] == "loki"
    )
    traces_target = next(
        panel["targets"][0]
        for panel in dashboard["panels"]
        if panel["datasource"]["type"] == "tempo"
    )
    assert 'scenario=~"${scenario:regex}"' in logs_target["expr"]
    assert (
        'span."aiqa.scenario" =~ "${scenario:regex}"' in traces_target["query"]
    )


def test_dashboard_uses_the_learner_facing_high_risk_panel_name() -> None:
    dashboard = json.loads(
        Path("deploy/grafana-cloud/dashboards/ai-quality.json").read_text()
    )
    titles = {panel["title"] for panel in dashboard["panels"]}

    assert "High-risk prediction rate" in titles
    assert "Positive mortality-risk rate" not in titles


def test_dashboard_keeps_p5_collection_visible_during_p6_analysis() -> None:
    dashboard = json.loads(
        Path("deploy/grafana-cloud/dashboards/ai-quality.json").read_text()
    )

    assert dashboard["time"] == {"from": "now-2h", "to": "now"}
