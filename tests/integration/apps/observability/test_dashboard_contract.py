"""Dashboard queries must follow the runtime telemetry contract."""

import json
import re
from pathlib import Path

from risk_api.adapters.config import load_api_config

DASHBOARD_PATH = Path("deploy/grafana-cloud/dashboards/ai-quality.json")
HANGUL = re.compile(r"[가-힣]")
SECTION_HEADING = re.compile(r"^\*\*[^*]+\*\*\s*$", re.MULTILINE)
ROW_TITLES = ("Service", "Prediction quality", "Investigate")
PANEL_TITLES = (
    "가이드라인",
    "Request rate",
    "5xx rate",
    "P95 latency",
    "Latency heatmap",
    "High-risk prediction rate",
    "Risk score P95",
    "Missing features P95",
    "Risk score heatmap",
    "Missing features heatmap",
    "Recent Risk API logs",
    "Risk API traces",
)
GUIDE_TOKENS = (
    "course-session",
    "5xx",
    "422",
    "heatmap",
    "record_id",
    "Explore",
)
REQUEST_PANEL_TITLES = ("Request rate", "5xx rate", "P95 latency")
HEATMAP_METRICS = {
    "Latency heatmap": "aiqa_risk_request_duration_seconds_bucket",
    "Risk score heatmap": "aiqa_risk_score_bucket",
    "Missing features heatmap": "aiqa_risk_missing_features_bucket",
}
LOGS_EXPR = (
    '{service_name="risk-api", environment=~"$environment"} | json | '
    'event=~"http.request.completed|risk.prediction.completed|'
    'model.input.validation.failed" | scenario=~"${scenario:regex}" | '
    'request_id=~"${request_id}" | run_id=~"${run_id}" | '
    'trace_id=~"${trace_id}"'
)


def _load_dashboard() -> dict:
    return json.loads(DASHBOARD_PATH.read_text())


def _panels_by_title(dashboard: dict) -> dict[str, dict]:
    return {panel["title"]: panel for panel in dashboard["panels"]}


def _prometheus_targets(dashboard: dict) -> list[dict]:
    return [
        target
        for panel in dashboard["panels"]
        if panel.get("datasource", {}).get("type") == "prometheus"
        for target in panel.get("targets", [])
    ]


def test_dashboard_uses_declared_metrics_and_all_three_datasources() -> None:
    dashboard = _load_dashboard()
    config = load_api_config(Path("configs/serving/api.yaml"))
    queries = " ".join(
        str(target)
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    )
    datasource_uids = {
        panel["datasource"]["uid"]
        for panel in dashboard["panels"]
        if panel.get("datasource", {}).get("uid", "").startswith("__AIQA_")
    }
    panels = _panels_by_title(dashboard)
    request_queries = [
        target["expr"]
        for title in REQUEST_PANEL_TITLES
        for target in panels[title].get("targets", [])
    ]

    for metric_name in config.observability.metrics.model_dump().values():
        assert metric_name in queries
    assert set(REQUEST_PANEL_TITLES) <= set(panels)
    assert all('route="/v1/predict"' in query for query in request_queries)
    assert datasource_uids == {
        "__AIQA_METRICS_UID__",
        "__AIQA_LOGS_UID__",
        "__AIQA_TRACES_UID__",
    }
    assert dashboard["uid"] == "tta-aiqa-quality"
    assert dashboard["schemaVersion"] == 41


def test_dashboard_filters_and_names_every_metric_series_by_bounded_scenario() -> None:
    dashboard = _load_dashboard()
    config = load_api_config(Path("configs/serving/api.yaml"))
    variables = {
        variable["name"]: variable for variable in dashboard["templating"]["list"]
    }
    scenario = variables["scenario"]
    metric_targets = _prometheus_targets(dashboard)
    timeseries_targets = [
        target
        for panel in dashboard["panels"]
        if panel.get("type") == "timeseries"
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
    assert timeseries_targets
    assert all(
        "{{scenario}}" in target["legendFormat"] for target in timeseries_targets
    )
    logs_target = next(
        panel["targets"][0]
        for panel in dashboard["panels"]
        if panel.get("datasource", {}).get("type") == "loki"
    )
    traces_panel = next(
        panel
        for panel in dashboard["panels"]
        if panel.get("datasource", {}).get("type") == "tempo"
    )
    traces_target = traces_panel["targets"][0]
    assert logs_target["expr"] == LOGS_EXPR
    assert 'record_id=~"${record_id}"' not in logs_target["expr"]
    assert traces_panel["type"] == "table"
    assert traces_target["queryType"] == "traceql"
    assert (
        'span."aiqa.scenario" =~ "${scenario:regex}"' in traces_target["query"]
    )
    assert 'span."aiqa.request_id" =~ "${request_id}"' in traces_target["query"]
    assert 'span."aiqa.run_id" =~ "${run_id}"' in traces_target["query"]
    assert 'span."aiqa.record_id"' not in traces_target["query"]


def test_dashboard_uses_the_learner_facing_high_risk_panel_name() -> None:
    dashboard = _load_dashboard()
    titles = {panel["title"] for panel in dashboard["panels"]}

    assert "High-risk prediction rate" in titles
    assert "Positive mortality-risk rate" not in titles


def test_dashboard_keeps_p5_collection_visible_during_p6_analysis() -> None:
    dashboard = _load_dashboard()

    assert dashboard["time"] == {"from": "now-2h", "to": "now"}


def test_dashboard_lets_learners_filter_logs_and_traces_by_correlation_ids() -> None:
    dashboard = _load_dashboard()
    variables = {
        variable["name"]: variable for variable in dashboard["templating"]["list"]
    }

    for name in ("request_id", "run_id", "trace_id"):
        assert variables[name]["type"] == "textbox"
        assert variables[name]["query"] == ".*"
    assert "record_id" not in variables
    assert {variable["name"] for variable in dashboard["templating"]["list"]} == {
        "environment",
        "scenario",
        "request_id",
        "run_id",
        "trace_id",
    }
    metric_queries = [target["expr"] for target in _prometheus_targets(dashboard)]
    assert metric_queries
    assert all(
        "request_id" not in query
        and "run_id" not in query
        and "trace_id" not in query
        and "record_id" not in query
        for query in metric_queries
    )


def test_dashboard_uses_frozen_row_and_panel_titles() -> None:
    dashboard = _load_dashboard()
    row_titles = tuple(
        panel["title"] for panel in dashboard["panels"] if panel["type"] == "row"
    )
    content_titles = tuple(
        panel["title"] for panel in dashboard["panels"] if panel["type"] != "row"
    )

    assert row_titles == ROW_TITLES
    assert content_titles == PANEL_TITLES
    assert "Error rate" not in content_titles


def test_dashboard_uses_count_rates_instead_of_clamped_ratios() -> None:
    dashboard = _load_dashboard()
    document = DASHBOARD_PATH.read_text()
    panels = _panels_by_title(dashboard)
    five_xx_expr = panels["5xx rate"]["targets"][0]["expr"]
    high_risk_expr = panels["High-risk prediction rate"]["targets"][0]["expr"]

    assert "clamp_min" not in document
    assert "1e-9" not in document
    assert "Error rate" not in document
    assert panels["5xx rate"]["type"] == "timeseries"
    assert 'status_code=~"5.."' in five_xx_expr
    assert five_xx_expr.count("rate(") == 1
    assert "clamp_min" not in five_xx_expr
    assert panels["High-risk prediction rate"]["type"] == "timeseries"
    assert 'prediction="high_risk"' in high_risk_expr
    assert high_risk_expr.count("rate(") == 1
    assert "clamp_min" not in high_risk_expr


def test_dashboard_adds_histogram_heatmaps_for_latency_score_and_missing() -> None:
    dashboard = _load_dashboard()
    panels = _panels_by_title(dashboard)

    for title, metric_name in HEATMAP_METRICS.items():
        panel = panels[title]
        expr = panel["targets"][0]["expr"]
        assert panel["type"] == "heatmap"
        assert metric_name in expr
        assert "sum by (le, scenario)" in expr
        assert 'scenario=~"${scenario:regex}"' in expr


def test_dashboard_explains_panels_in_korean() -> None:
    dashboard = _load_dashboard()
    panels = _panels_by_title(dashboard)
    guide = panels["가이드라인"]
    content = guide["options"]["content"]

    assert guide["type"] == "text"
    assert guide["options"]["mode"] == "markdown"
    assert HANGUL.search(content)
    assert all(token in content for token in GUIDE_TOKENS)
    assert HANGUL.search(dashboard["description"])
    assert "제목 옆" in content
    assert "해설" in content
    assert "관측된 5xx" in content
    assert "운영 JSONL" in content
    assert all(title in content for title in ROW_TITLES)
    assert SECTION_HEADING.search(content) is None
    assert len(dashboard["description"]) >= 80
    for title in PANEL_TITLES:
        if title == "가이드라인":
            continue
        description = panels[title]["description"]
        assert HANGUL.search(description)
        assert "이 그래프" in description
        assert SECTION_HEADING.search(description) is None
        assert len(description) >= 180
    assert "받은 요청" in panels["Request rate"]["description"]
    assert "가로축" in panels["Risk score heatmap"]["description"]
    assert "세로축 위쪽" in panels["Missing features heatmap"]["description"]
    assert "로그만 보인다면" not in panels["Recent Risk API logs"]["description"]
    for title in ROW_TITLES:
        description = panels[title]["description"]
        assert HANGUL.search(description)
        assert SECTION_HEADING.search(description) is None
        assert len(description) >= 80
