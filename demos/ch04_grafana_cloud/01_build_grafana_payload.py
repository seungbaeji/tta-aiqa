"""Chapter 4 Demo: prepare Grafana Cloud import artifacts."""

from __future__ import annotations

import pandas as pd
from ai_quality.common.config import load_yaml
from ai_quality.common.paths import artifact_path, config_path, data_path
from ai_quality.observability.application.build_quality_snapshot import (
    build_quality_snapshot,
)
from ai_quality.observability.application.generate_sample_events import (
    generate_sample_events,
)
from ai_quality.observability.infrastructure.grafana_cloud_exporter import (
    emit_grafana_cloud_payload,
)
from ai_quality.observability.infrastructure.grafana_dashboard import (
    write_dashboard_jsons,
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


def main() -> None:
    """Write Grafana dashboard artifact for cloud import."""
    config = load_yaml(config_path("operations", "grafana_cloud.yaml"))
    feature_config = load_yaml(config_path("validation", "model_features.yaml"))
    baseline_events = generate_sample_events(scenario="normal")
    events = generate_sample_events(scenario="anomaly")
    snapshot = build_quality_snapshot(events)
    feature_comparisons = compare_input_distribution(
        baseline=pd.read_csv(data_path("serving_requests_valid.csv")),
        current=pd.read_csv(data_path("serving_requests_current.csv")),
        feature_columns=list(feature_config["feature_columns"]),
    )
    score_comparison = compare_score_distribution(baseline_events, events)

    metrics_path = artifact_path("metrics", "chapter_04_anomaly.prom")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
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
        render_prometheus_metrics(snapshot, events) + drift_metrics,
        encoding="utf-8",
    )
    dashboard_paths = write_dashboard_jsons(artifact_path("grafana"))
    payload_path = emit_grafana_cloud_payload(
        events=events[:10],
        snapshot=snapshot,
        logs_datasource=str(config["logs_datasource"]),
        metrics_datasource=str(config["metrics_datasource"]),
        labels=dict(config["labels"]),
        output_path=artifact_path("grafana", "grafana_cloud_payload_preview.json"),
        extra_prometheus_metrics=drift_metrics,
    )

    print("Grafana Cloud demo artifact")
    print(dashboard_paths["ai_quality_overview_dashboard.json"])
    print(dashboard_paths["ai_quality_details_dashboard.json"])
    print(payload_path)
    print(metrics_path)
    print("Import this JSON into Grafana Cloud Dashboards.")


if __name__ == "__main__":
    main()
