"""Grafana Cloud demo payload builder.

This module intentionally does not send data to Grafana Cloud. It creates a
reviewable payload preview so the course can discuss labels, log fields, and
metrics without requiring student credentials.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.observability.domain.quality_snapshot import QualitySnapshot
from ai_quality.observability.infrastructure.prometheus_text import (
    render_prometheus_metrics,
)


@dataclass(frozen=True)
class GrafanaCloudPayload:
    """Preview of logs and metrics intended for Grafana Cloud review."""

    logs_datasource: str
    metrics_datasource: str
    labels: dict[str, str]
    log_events: list[dict[str, str | float | int | bool | None]]
    prometheus_metrics: str


# docs:start emit_grafana_cloud_payload
def emit_grafana_cloud_payload(
    events: list[PredictionEvent],
    snapshot: QualitySnapshot,
    logs_datasource: str,
    metrics_datasource: str,
    labels: dict[str, str],
    output_path: Path,
    extra_prometheus_metrics: str = "",
) -> Path:
    """Write a Grafana Cloud payload preview as JSON."""
    payload = GrafanaCloudPayload(
        logs_datasource=logs_datasource,
        metrics_datasource=metrics_datasource,
        labels=labels,
        log_events=[
            {
                **event.to_dict(),
                **{f"label_{key}": value for key, value in labels.items()},
            }
            for event in events
        ],
        prometheus_metrics=render_prometheus_metrics(snapshot, events)
        + extra_prometheus_metrics,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(payload), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path
# docs:end emit_grafana_cloud_payload
