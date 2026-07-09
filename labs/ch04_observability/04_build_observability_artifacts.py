"""Build observability artifacts for logs, metrics, and Grafana."""

from __future__ import annotations

import pandas as pd
from ai_quality.common.config import load_yaml
from ai_quality.common.paths import artifact_path, config_path, data_path
from ai_quality.labs.ch04_observability import anomaly_log_path, normal_log_path
from ai_quality.labs.ch05_qa_strategy import baseline_events, current_events
from ai_quality.observability.application.analyze_quality_signal import (
    analyze_quality_signal,
)
from ai_quality.observability.application.build_quality_snapshot import (
    build_quality_snapshot,
)
from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.observability.infrastructure.grafana_cloud_exporter import (
    emit_grafana_cloud_payload,
)
from ai_quality.observability.infrastructure.grafana_dashboard import (
    write_dashboard_jsons,
)
from ai_quality.observability.infrastructure.jsonl_event_store import (
    write_events_jsonl,
)
from ai_quality.observability.infrastructure.prometheus_text import (
    render_drift_metrics,
    render_prometheus_metrics,
)
from ai_quality.qa_strategy.application.analyze_prediction_shift import (
    compare_score_distribution,
)
from ai_quality.qa_strategy.application.detect_input_shift import (
    compare_input_distribution,
)
from ai_quality.qa_strategy.application.trace_quality_issue import trace_quality_issue
from ai_quality.qa_strategy.infrastructure.report_markdown_writer import (
    render_issue_trace_markdown,
)


def render_validation_failure_examples(events: list[PredictionEvent]) -> str:
    """Render representative validation failures for QA handoff."""
    failure_events = [event for event in events if event.validation_failure][:5]
    lines = [
        "# Chapter 04 Validation Failure Examples",
        "",
        (
            "이 파일은 4장 운영 관측 보고서에서 검증 실패 owner와 "
            "next action을 지정하기 위한 prepared evidence입니다."
        ),
        "",
        (
            "| request_id | client_id | source_system | failed_field | "
            "error_category | error_detail | owner | next_action |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for event in failure_events:
        failed_field = event.failed_field or "-"
        lines.append(
            "| "
            f"{event.request_id} | "
            f"{event.client_id or '-'} | "
            f"{event.source_system or '-'} | "
            f"{failed_field} | "
            f"{event.error_category or '-'} | "
            f"{event.error_detail or '-'} | "
            f"{event.owner or '-'} | "
            f"{failed_field} 입력 생성 로직과 API schema 변경 이력을 확인합니다. |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Generate log, Prometheus, dashboard, and Grafana payload artifacts."""
    normal_events = baseline_events()
    anomaly_events = current_events()
    normal_path = write_events_jsonl(normal_events, normal_log_path())
    anomaly_path = write_events_jsonl(anomaly_events, anomaly_log_path())

    baseline_snapshot = build_quality_snapshot(normal_events)
    snapshot = build_quality_snapshot(anomaly_events)
    metrics_path = artifact_path("metrics", "chapter_04_anomaly.prom")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    feature_config = load_yaml(config_path("validation", "model_features.yaml"))
    feature_comparisons = compare_input_distribution(
        baseline=pd.read_csv(data_path("serving_requests_valid.csv")),
        current=pd.read_csv(data_path("serving_requests_current.csv")),
        feature_columns=list(feature_config["feature_columns"]),
    )
    score_comparison = compare_score_distribution(
        baseline_events=normal_events,
        current_events=anomaly_events,
    )
    drift_metrics = render_drift_metrics(
        feature_mean_deltas={
            comparison.feature: comparison.mean_delta
            for comparison in feature_comparisons
            if comparison.shifted
        },
        average_score_delta=score_comparison.average_score_delta,
        high_risk_rate_delta=score_comparison.high_risk_rate_delta,
        input_histograms=[
            comparison for comparison in feature_comparisons if comparison.shifted
        ],
    )
    metrics_path.write_text(
        render_prometheus_metrics(snapshot, anomaly_events) + drift_metrics,
        encoding="utf-8",
    )
    issue_trace = trace_quality_issue(
        feature_comparisons=feature_comparisons,
        score_comparison=score_comparison,
        quality_report=analyze_quality_signal(baseline_snapshot, snapshot),
        current_events=anomaly_events,
    )
    issue_trace_path = artifact_path("reports", "quality_issue_trace.md")
    issue_trace_path.parent.mkdir(parents=True, exist_ok=True)
    issue_trace_path.write_text(
        render_issue_trace_markdown(issue_trace),
        encoding="utf-8",
    )

    validation_failure_path = artifact_path(
        "reports", "chapter_04_validation_failure_examples.md"
    )
    validation_failure_path.parent.mkdir(parents=True, exist_ok=True)
    validation_failure_path.write_text(
        render_validation_failure_examples(anomaly_events),
        encoding="utf-8",
    )

    config = load_yaml(config_path("operations", "grafana_cloud.yaml"))
    dashboard_paths = write_dashboard_jsons(artifact_path("grafana"))
    payload_path = emit_grafana_cloud_payload(
        events=anomaly_events[:10],
        snapshot=snapshot,
        logs_datasource=str(config["logs_datasource"]),
        metrics_datasource=str(config["metrics_datasource"]),
        labels=dict(config["labels"]),
        output_path=artifact_path("grafana", "grafana_cloud_payload_preview.json"),
        extra_prometheus_metrics=drift_metrics,
    )

    print(f"normal_log={normal_path}")
    print(f"anomaly_log={anomaly_path}")
    print(f"metrics={metrics_path}")
    print(f"quality_issue_trace={issue_trace_path}")
    print(f"overview_dashboard={dashboard_paths['ai_quality_overview_dashboard.json']}")
    print(f"details_dashboard={dashboard_paths['ai_quality_details_dashboard.json']}")
    print(f"grafana_payload_preview={payload_path}")
    print(f"validation_failure_examples={validation_failure_path}")


if __name__ == "__main__":
    main()
