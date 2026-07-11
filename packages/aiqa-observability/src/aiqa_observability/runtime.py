"""Runtime observability helpers for prediction events."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd
from aiqa_core.contracts import NEGATIVE_LABEL, POSITIVE_LABEL


@dataclass(frozen=True)
class TraceSettings:
    endpoint: str
    timeout_seconds: float
    service_name: str
    deployment_environment: str


class ObservabilityState:
    """Keep lightweight runtime signals for Prometheus and trace correlation."""

    def __init__(
        self,
        baseline_data_path: Path,
        input_distribution_features: tuple[str, ...],
        score_buckets: tuple[float, ...],
    ) -> None:
        self._lock = Lock()
        self._events: list[dict[str, Any]] = []
        self._features = input_distribution_features
        self._score_buckets = score_buckets
        self._baseline = load_baseline_distribution(
            baseline_data_path,
            input_distribution_features,
        )

    def record(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._events.append(event)

    def render_prometheus(self) -> str:
        with self._lock:
            events = list(self._events)
            baseline = self._baseline

        request_total = len(events)
        error_total = sum(1 for event in events if int(event["status_code"]) >= 400)
        validation_failure_total = sum(
            1 for event in events if bool(event["validation_failure"])
        )
        valid_events = [event for event in events if not event["validation_failure"]]
        scored_events = [
            event for event in events if isinstance(event.get("score"), int | float)
        ]
        valid_scored_events = [
            event
            for event in valid_events
            if isinstance(event.get("score"), int | float)
        ]

        lines = [
            "# TYPE ai_quality_request_total counter",
            f"ai_quality_request_total {request_total}",
            "# TYPE ai_quality_error_total counter",
            f"ai_quality_error_total {error_total}",
            "# TYPE ai_quality_validation_failure_total counter",
            f"ai_quality_validation_failure_total {validation_failure_total}",
            "# TYPE ai_quality_latency_average_ms gauge",
            f"ai_quality_latency_average_ms {average(events, 'latency_ms'):.3f}",
            "# TYPE ai_quality_score_average gauge",
            f"ai_quality_score_average {average(scored_events, 'score'):.6f}",
            "# TYPE ai_quality_high_risk_rate gauge",
            f"ai_quality_high_risk_rate {prediction_rate(scored_events):.6f}",
            "# TYPE ai_quality_valid_request_total counter",
            f"ai_quality_valid_request_total {len(valid_events)}",
            "# TYPE ai_quality_valid_score_average gauge",
            f"ai_quality_valid_score_average "
            f"{average(valid_scored_events, 'score'):.6f}",
            "# TYPE ai_quality_valid_high_risk_rate gauge",
            f"ai_quality_valid_high_risk_rate "
            f"{prediction_rate(valid_scored_events):.6f}",
            "# TYPE ai_quality_prediction_count gauge",
        ]
        for scope, scoped_events in (
            ("all", scored_events),
            ("valid", valid_scored_events),
        ):
            for prediction in (POSITIVE_LABEL, NEGATIVE_LABEL):
                count = sum(
                    1
                    for event in scoped_events
                    if event.get("prediction") == prediction
                )
                lines.append(
                    "ai_quality_prediction_count"
                    f'{{prediction="{prediction}",scope="{scope}"}} {count}'
                )

        lines.append("# TYPE ai_quality_score_bucket_count gauge")
        for scope, scoped_events in (
            ("all", scored_events),
            ("valid", valid_scored_events),
        ):
            for bucket in bucket_labels(self._score_buckets):
                count = sum(
                    1
                    for event in scoped_events
                    if bucket_for(float(event["score"]), self._score_buckets)
                    == bucket
                )
                lines.append(
                    "ai_quality_score_bucket_count"
                    f'{{bucket="{bucket}",scope="{scope}"}} {count}'
                )

        lines.extend(
            render_input_distribution_metrics(events, baseline, self._features)
        )
        return "\n".join(lines) + "\n"


def append_prediction_event(event: dict[str, Any], events_path: Path) -> None:
    """Append one prediction event as JSONL and emit it as structured stdout."""
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(json.dumps(event, ensure_ascii=False), flush=True)


def average(events: list[dict[str, Any]], key: str) -> float:
    values = [float(event[key]) for event in events if event.get(key) is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)


def prediction_rate(events: list[dict[str, Any]]) -> float:
    if not events:
        return 0.0
    high_risk_count = sum(
        1 for event in events if event.get("prediction") == POSITIVE_LABEL
    )
    return high_risk_count / len(events)


def bucket_labels(edges: tuple[float, ...]) -> list[str]:
    return [
        f"{edges[index]:.1f}-{edges[index + 1]:.1f}"
        for index in range(len(edges) - 1)
    ]


def bucket_for(value: float, edges: tuple[float, ...]) -> str:
    labels = bucket_labels(edges)
    for index, label in enumerate(labels):
        lower = edges[index]
        upper = edges[index + 1]
        if lower <= value < upper or (index == len(labels) - 1 and value <= upper):
            return label
    if value < edges[0]:
        return labels[0]
    return labels[-1]


def load_baseline_distribution(
    path: Path,
    features: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    """Load baseline feature statistics used by drift panels."""
    if not path.exists():
        return {}

    dataframe = pd.read_csv(path)
    baseline: dict[str, dict[str, Any]] = {}
    for feature in features:
        if feature not in dataframe.columns:
            continue
        values = [float(value) for value in dataframe[feature].dropna().tolist()]
        if not values:
            continue
        edges = histogram_edges(values)
        baseline[feature] = {
            "mean": sum(values) / len(values),
            "edges": edges,
            "counts": histogram_counts(values, edges),
        }
    return baseline


def histogram_edges(values: list[float], bin_count: int = 5) -> tuple[float, ...]:
    lower = min(values)
    upper = max(values)
    if lower == upper:
        upper = lower + 1.0
    width = (upper - lower) / bin_count
    return tuple(lower + width * index for index in range(bin_count + 1))


def histogram_labels(edges: tuple[float, ...]) -> list[str]:
    return [
        f"{edges[index]:.2f}~{edges[index + 1]:.2f}"
        for index in range(len(edges) - 1)
    ]


def histogram_counts(values: list[float], edges: tuple[float, ...]) -> list[int]:
    counts = [0 for _ in range(len(edges) - 1)]
    for value in values:
        for index in range(len(counts)):
            lower = edges[index]
            upper = edges[index + 1]
            if lower <= value < upper or (index == len(counts) - 1 and value <= upper):
                counts[index] += 1
                break
    return counts


def render_input_distribution_metrics(
    events: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    features: tuple[str, ...],
) -> list[str]:
    lines = ["# TYPE ai_quality_input_mean_delta gauge"]
    current_values = {
        feature: [
            float(event["features"][feature])
            for event in events
            if not event["validation_failure"] and feature in event.get("features", {})
        ]
        for feature in features
    }
    for feature, values in current_values.items():
        baseline_mean = baseline.get(feature, {}).get("mean")
        current_mean = sum(values) / len(values) if values else baseline_mean
        delta = (
            0.0
            if baseline_mean is None or current_mean is None
            else float(current_mean) - float(baseline_mean)
        )
        lines.append(f'ai_quality_input_mean_delta{{feature="{feature}"}} {delta:.6f}')

    lines.append("# TYPE ai_quality_input_histogram_count gauge")
    for feature, baseline_stats in baseline.items():
        edges = baseline_stats["edges"]
        labels = histogram_labels(edges)
        baseline_counts = baseline_stats["counts"]
        current_counts = histogram_counts(current_values.get(feature, []), edges)
        for label, count in zip(labels, baseline_counts, strict=True):
            lines.append(
                "ai_quality_input_histogram_count"
                f'{{feature="{feature}",bucket="{label}",scope="baseline"}} {count}'
            )
        for label, count in zip(labels, current_counts, strict=True):
            lines.append(
                "ai_quality_input_histogram_count"
                f'{{feature="{feature}",bucket="{label}",scope="current"}} {count}'
            )
    return lines


def _hex_digest(value: str, length: int) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:length]


def tempo_trace_id(course_trace_id: str) -> str:
    return _hex_digest(course_trace_id, 32)


def span_id(value: str) -> str:
    return _hex_digest(value, 16)


def otlp_attribute(key: str, value: str | int | float | bool | None) -> dict[str, Any]:
    if isinstance(value, bool):
        encoded: dict[str, Any] = {"boolValue": value}
    elif isinstance(value, int):
        encoded = {"intValue": str(value)}
    elif isinstance(value, float):
        encoded = {"doubleValue": value}
    else:
        encoded = {"stringValue": "" if value is None else str(value)}
    return {"key": key, "value": encoded}


def otlp_span(
    *,
    trace_id: str,
    span_id_value: str,
    parent_span_id: str | None,
    name: str,
    kind: int,
    start_ns: int,
    duration_ms: float,
    attributes: list[dict[str, Any]],
) -> dict[str, Any]:
    span: dict[str, Any] = {
        "traceId": trace_id,
        "spanId": span_id_value,
        "name": name,
        "kind": kind,
        "startTimeUnixNano": str(start_ns),
        "endTimeUnixNano": str(start_ns + int(max(duration_ms, 0.1) * 1_000_000)),
        "attributes": attributes,
    }
    if parent_span_id:
        span["parentSpanId"] = parent_span_id
    return span


def send_trace(
    event: dict[str, Any],
    start_ns: int,
    settings: TraceSettings,
) -> None:
    """Send one request trace to the configured OTLP/HTTP endpoint."""
    if not settings.endpoint:
        return

    course_trace_id = str(event["trace_id"])
    trace_id = tempo_trace_id(course_trace_id)
    root_span_id = span_id(f"{course_trace_id}:server:predict")
    common_attributes = [
        otlp_attribute("deployment.environment", settings.deployment_environment),
        otlp_attribute("request_id", event["request_id"]),
        otlp_attribute("course_trace_id", course_trace_id),
        otlp_attribute("trace_id", course_trace_id),
        otlp_attribute("model_version", event.get("model_version")),
        otlp_attribute("threshold", event.get("threshold")),
        otlp_attribute("prediction", event.get("prediction")),
        otlp_attribute("validation_failure", event["validation_failure"]),
    ]
    spans = [
        otlp_span(
            trace_id=trace_id,
            span_id_value=root_span_id,
            parent_span_id=None,
            name="POST /predict",
            kind=2,
            start_ns=start_ns,
            duration_ms=float(event["latency_ms"]),
            attributes=[
                *common_attributes,
                otlp_attribute("http.method", "POST"),
                otlp_attribute("http.status_code", event["status_code"]),
                otlp_attribute("score", event.get("score")),
            ],
        )
    ]
    child_specs = (
        ("validate_payload", 0.0, 8.0),
        ("score_model", 8.0, max(3.0, float(event["latency_ms"]) - 16.0)),
        ("emit_observability", max(12.0, float(event["latency_ms"]) - 8.0), 8.0),
    )
    for name, offset_ms, duration_ms in child_specs:
        spans.append(
            otlp_span(
                trace_id=trace_id,
                span_id_value=span_id(f"{course_trace_id}:server:{name}"),
                parent_span_id=root_span_id,
                name=name,
                kind=1,
                start_ns=start_ns + int(offset_ms * 1_000_000),
                duration_ms=duration_ms,
                attributes=common_attributes,
            )
        )

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        otlp_attribute("service.name", settings.service_name),
                        otlp_attribute(
                            "deployment.environment",
                            settings.deployment_environment,
                        ),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "simple-aiqa-mlops",
                            "version": "0.1.0",
                        },
                        "spans": spans,
                    }
                ],
            }
        ]
    }
    request = urllib.request.Request(
        settings.endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.timeout_seconds):
            return
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "warning",
                    "event": "otlp_trace_send_failed",
                    "request_id": event["request_id"],
                    "trace_id": event["trace_id"],
                    "error": str(error),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
