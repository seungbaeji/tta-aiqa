"""Build OTLP trace payloads from prediction events."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from typing import Any

from ai_quality.observability.domain.prediction_event import PredictionEvent


def representative_tempo_trace_id(course_trace_id: str) -> str:
    """Return the deterministic Tempo trace id used by the course demo."""
    return _hex_digest(course_trace_id, 32)


def build_otlp_trace_payload(
    *,
    events: list[PredictionEvent],
    sample_size: int,
    preserve_timestamps: bool,
) -> dict[str, Any]:
    """Build a small OTLP/HTTP JSON trace payload from prediction events."""
    sample_events = events[:sample_size]
    if not sample_events:
        msg = "no prediction events found; build observability artifacts first"
        raise ValueError(msg)

    now_ns = time.time_ns()
    spans_by_service: dict[str, list[dict[str, Any]]] = {}
    for index, event in enumerate(sample_events):
        trace_id = representative_tempo_trace_id(event.trace_id)
        client_span_id = _hex_digest(f"{event.trace_id}:client:predict", 16)
        root_span_id = _hex_digest(f"{event.trace_id}:server:predict", 16)
        start_ns = now_ns + index * 200_000_000
        if preserve_timestamps:
            parsed_timestamp = datetime.fromisoformat(
                event.timestamp.replace("Z", "+00:00")
            )
            start_ns = int(parsed_timestamp.timestamp() * 1_000_000_000)

        common_attributes = [
            _attribute("deployment.environment", "training"),
            _attribute("request_id", event.request_id),
            _attribute("course_trace_id", event.trace_id),
            _attribute("model_version", event.model_version),
            _attribute("threshold", event.threshold),
            _attribute("prediction", event.prediction),
            _attribute("validation_failure", event.validation_failure),
        ]
        _add_span(
            spans_by_service,
            "qa-client",
            _span(
                trace_id=trace_id,
                span_id=client_span_id,
                parent_span_id=None,
                name="POST /predict",
                kind=3,
                start_ns=start_ns,
                duration_ms=event.latency_ms,
                attributes=[
                    *common_attributes,
                    _attribute("http.method", "POST"),
                    _attribute("http.status_code", event.status_code),
                ],
            ),
        )
        _add_span(
            spans_by_service,
            "ai-quality-serving",
            _span(
                trace_id=trace_id,
                span_id=root_span_id,
                parent_span_id=client_span_id,
                name="POST /predict",
                kind=2,
                start_ns=start_ns,
                duration_ms=event.latency_ms,
                attributes=[
                    *common_attributes,
                    _attribute("http.method", "POST"),
                    _attribute("http.status_code", event.status_code),
                    _attribute("score", event.score),
                ],
            ),
        )
        child_specs = [
            ("input-validator", "validate_payload", 0.0, 8.0),
            ("model-runtime", "score_model", 10.0, max(5.0, event.latency_ms - 35.0)),
            (
                "observability-pipeline",
                "emit_observability",
                max(20.0, event.latency_ms - 20.0),
                12.0,
            ),
        ]
        for target_service, name, offset_ms, duration_ms in child_specs:
            client_child_span_id = _hex_digest(f"{event.trace_id}:client:{name}", 16)
            server_child_span_id = _hex_digest(f"{event.trace_id}:server:{name}", 16)
            child_start_ns = start_ns + int(offset_ms * 1_000_000)
            _add_span(
                spans_by_service,
                "ai-quality-serving",
                _span(
                    trace_id=trace_id,
                    span_id=client_child_span_id,
                    parent_span_id=root_span_id,
                    name=name,
                    kind=3,
                    start_ns=child_start_ns,
                    duration_ms=duration_ms,
                    attributes=common_attributes,
                ),
            )
            _add_span(
                spans_by_service,
                target_service,
                _span(
                    trace_id=trace_id,
                    span_id=server_child_span_id,
                    parent_span_id=client_child_span_id,
                    name=name,
                    kind=2,
                    start_ns=child_start_ns,
                    duration_ms=duration_ms,
                    attributes=common_attributes,
                ),
            )

    return {
        "resourceSpans": [
            _resource_scope_spans(service_name, service_spans)
            for service_name, service_spans in spans_by_service.items()
        ]
    }


def count_spans(payload: dict[str, Any]) -> int:
    """Return span count from a course OTLP payload."""
    count = 0
    for resource_span in payload["resourceSpans"]:
        for scope_span in resource_span["scopeSpans"]:
            count += len(scope_span["spans"])
    return count


def _add_span(
    spans_by_service: dict[str, list[dict[str, Any]]],
    service_name: str,
    span: dict[str, Any],
) -> None:
    spans_by_service.setdefault(service_name, []).append(span)


def _resource_scope_spans(
    service_name: str,
    spans: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "resource": {
            "attributes": [
                _attribute("service.name", service_name),
                _attribute("deployment.environment", "training"),
            ]
        },
        "scopeSpans": [
            {
                "scope": {
                    "name": "ai-quality-training-demo",
                    "version": "0.1.0",
                },
                "spans": spans,
            }
        ],
    }


def _hex_digest(value: str, length: int) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:length]


def _attribute(key: str, value: str | int | float | bool) -> dict[str, Any]:
    if isinstance(value, bool):
        encoded: dict[str, Any] = {"boolValue": value}
    elif isinstance(value, int):
        encoded = {"intValue": str(value)}
    elif isinstance(value, float):
        encoded = {"doubleValue": value}
    else:
        encoded = {"stringValue": value}
    return {"key": key, "value": encoded}


def _span(
    *,
    trace_id: str,
    span_id: str,
    parent_span_id: str | None,
    name: str,
    kind: int,
    start_ns: int,
    duration_ms: float,
    attributes: list[dict[str, Any]],
) -> dict[str, Any]:
    span: dict[str, Any] = {
        "traceId": trace_id,
        "spanId": span_id,
        "name": name,
        "kind": kind,
        "startTimeUnixNano": str(start_ns),
        "endTimeUnixNano": str(start_ns + int(duration_ms * 1_000_000)),
        "attributes": attributes,
    }
    if parent_span_id:
        span["parentSpanId"] = parent_span_id
    return span
