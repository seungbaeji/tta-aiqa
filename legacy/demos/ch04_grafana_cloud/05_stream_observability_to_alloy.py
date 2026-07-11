"""Continuously append demo logs, refresh metrics, and send traces to Alloy."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from ai_quality.labs.ch04_observability import anomaly_log_path
from ai_quality.labs.ch05_qa_strategy import current_events
from ai_quality.observability.application.build_quality_snapshot import (
    build_quality_snapshot,
)
from ai_quality.observability.application.build_trace_payload import (
    build_otlp_trace_payload,
    count_spans,
    representative_tempo_trace_id,
)
from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.observability.infrastructure.jsonl_event_store import (
    read_events_jsonl,
)
from ai_quality.observability.infrastructure.otlp_http import post_otlp_json
from ai_quality.observability.infrastructure.prometheus_text import (
    render_prometheus_metrics,
)

DEFAULT_METRICS_PATH = Path("artifacts/metrics/chapter_04_anomaly.prom")
DEFAULT_ALLOY_OTLP_ENDPOINT = "http://127.0.0.1:4318/v1/traces"
DEFAULT_SOURCE_EVENT_PATH = Path("data/operational_current_stream_events.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Append chapter 4 demo events as a live stream for Grafana Alloy. "
            "Keep Alloy and 03_serve_metrics.py running in separate terminals."
        ),
    )
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument(
        "--source-event-file",
        type=Path,
        default=DEFAULT_SOURCE_EVENT_PATH,
        help=(
            "JSONL source events to read on every batch. "
            "Defaults to data/operational_current_stream_events.jsonl."
        ),
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=0,
        help="Stop after this many batches. 0 means stream until Ctrl-C.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=anomaly_log_path(),
        help="JSONL log file tailed by Alloy.",
    )
    parser.add_argument(
        "--metrics-file",
        type=Path,
        default=DEFAULT_METRICS_PATH,
        help="Prometheus text file served by 03_serve_metrics.py.",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ALLOY_OTLP_ENDPOINT,
        help="Local Alloy OTLP/HTTP traces endpoint.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Start from an empty log file and reset streamed metrics.",
    )
    parser.add_argument(
        "--skip-traces",
        action="store_true",
        help="Only append logs and refresh metrics; do not call Alloy OTLP.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    templates = load_source_events(args.source_event_file)

    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_file.parent.mkdir(parents=True, exist_ok=True)
    if args.reset:
        args.log_file.write_text("", encoding="utf-8")

    existing_events = [] if args.reset else read_existing_events(args.log_file)
    drift_metrics = read_existing_drift_metrics(args.metrics_file)
    emitted_events = list(existing_events)
    sequence = len(existing_events)
    batch_index = 0

    print(f"log_file={args.log_file}")
    print(f"metrics_file={args.metrics_file}")
    print(f"source_event_file={args.source_event_file}")
    print(f"source_event_count={len(templates)}")
    print(f"alloy_otlp_endpoint={args.endpoint}")
    print(f"existing_event_count={len(existing_events)}")
    print("stream_result=running")

    try:
        while args.max_batches == 0 or batch_index < args.max_batches:
            templates = load_source_events(args.source_event_file)
            batch = build_stream_batch(
                templates=templates,
                start_sequence=sequence,
                batch_size=args.batch_size,
            )
            append_events(args.log_file, batch)
            emitted_events.extend(batch)
            write_metrics(args.metrics_file, emitted_events, drift_metrics)

            first_trace_id = batch[0].trace_id
            tempo_trace_id = representative_tempo_trace_id(first_trace_id)
            span_count = 0
            if not args.skip_traces:
                span_count = send_traces(args.endpoint, batch)

            sequence += len(batch)
            batch_index += 1
            validation_failure_count = sum(
                event.validation_failure for event in emitted_events
            )
            print(
                "batch="
                f"{batch_index} "
                f"request_total={len(emitted_events)} "
                f"batch_size={len(batch)} "
                f"source_event_count={len(templates)} "
                f"validation_failures={validation_failure_count} "
                f"span_count={span_count} "
                f"course_trace_id={first_trace_id} "
                f"tempo_trace_id={tempo_trace_id} "
                f'traceql={{ .course_trace_id = "{first_trace_id}" }}',
                flush=True,
            )
            time.sleep(args.interval_seconds)
    except KeyboardInterrupt:
        print("stream_result=stopped")


def load_source_events(path: Path) -> list[PredictionEvent]:
    """Read the current source event file, falling back to course helpers."""
    if path.exists() and path.stat().st_size > 0:
        events = read_events_jsonl(path)
    else:
        events = current_events()
    if not events:
        raise SystemExit("no current events found; build course data first")
    return events


def build_stream_batch(
    *,
    templates: list[PredictionEvent],
    start_sequence: int,
    batch_size: int,
) -> list[PredictionEvent]:
    """Return one batch with fresh request ids, trace ids, and timestamps."""
    now = datetime.now(UTC)
    batch: list[PredictionEvent] = []
    for offset in range(batch_size):
        sequence = start_sequence + offset
        template = templates[sequence % len(templates)]
        batch.append(
            replace(
                template,
                timestamp=now.isoformat(),
                request_id=f"stream-{sequence:06d}",
                trace_id=f"stream-trace-{sequence // 3:06d}",
            )
        )
    return batch


def append_events(path: Path, events: list[PredictionEvent]) -> None:
    """Append events as JSON lines for Alloy file tailing."""
    with path.open("a", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


def write_metrics(
    path: Path,
    events: list[PredictionEvent],
    drift_metrics: str,
) -> None:
    """Refresh Prometheus text metrics for the current streamed total."""
    snapshot = build_quality_snapshot(events)
    path.write_text(
        render_prometheus_metrics(snapshot, events) + drift_metrics,
        encoding="utf-8",
    )


def send_traces(endpoint: str, events: list[PredictionEvent]) -> int:
    """Send one trace batch to the local Alloy OTLP receiver."""
    payload = build_otlp_trace_payload(
        events=events,
        sample_size=len(events),
        preserve_timestamps=False,
    )
    span_count = count_spans(payload)
    status, body = post_otlp_json(endpoint=endpoint, payload=payload)
    if status not in {200, 202, 204}:
        print(body, file=sys.stderr)
        raise SystemExit(f"alloy trace push failed: HTTP {status}")
    return span_count


def read_existing_events(path: Path) -> list[PredictionEvent]:
    """Read existing stream events if the log file already exists."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    return read_events_jsonl(path)


def read_existing_drift_metrics(path: Path) -> str:
    """Keep drift metric lines when refreshing the streamed metrics file."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    marker = "# TYPE ai_quality_input_mean_delta"
    if marker not in text:
        return ""
    return text[text.index(marker) :]


if __name__ == "__main__":
    main()
