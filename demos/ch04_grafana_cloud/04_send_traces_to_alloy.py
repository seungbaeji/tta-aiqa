"""Send sample chapter 4 traces to the local Alloy OTLP receiver."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai_quality.common.paths import artifact_path
from ai_quality.labs.ch04_observability import anomaly_log_path
from ai_quality.observability.application.build_trace_payload import (
    build_otlp_trace_payload,
    count_spans,
    representative_tempo_trace_id,
)
from ai_quality.observability.infrastructure.jsonl_event_store import (
    read_events_jsonl,
)
from ai_quality.observability.infrastructure.otlp_http import post_otlp_json

DEFAULT_TRACE_PREVIEW_PATH = Path("artifacts/traces/chapter_04_tempo_payload.json")
DEFAULT_ALLOY_OTLP_ENDPOINT = "http://127.0.0.1:4318/v1/traces"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send sample traces to a local Grafana Alloy OTLP receiver.",
    )
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ALLOY_OTLP_ENDPOINT,
        help="Local Alloy OTLP/HTTP traces endpoint.",
    )
    parser.add_argument(
        "--preview-path",
        type=Path,
        default=DEFAULT_TRACE_PREVIEW_PATH,
        help="Path where the OTLP JSON preview is written.",
    )
    parser.add_argument(
        "--preserve-timestamps",
        action="store_true",
        help="Use artifact timestamps instead of current timestamps.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write payload preview and print summary without sending.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    events = read_events_jsonl(anomaly_log_path())
    payload = build_otlp_trace_payload(
        events=events,
        sample_size=args.sample_size,
        preserve_timestamps=args.preserve_timestamps,
    )
    output_path = artifact_path("traces", args.preview_path.name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    span_count = count_spans(payload)
    course_trace_id = events[0].trace_id
    tempo_trace_id = representative_tempo_trace_id(course_trace_id)

    if args.dry_run:
        print("dry_run=True")
        print(f"trace_preview={output_path}")
        print(f"alloy_otlp_endpoint={args.endpoint}")
        print(f"sample_size={args.sample_size}")
        print(f"span_count={span_count}")
        print(f"tempo_trace_id={tempo_trace_id}")
        print(f'traceql={{ .course_trace_id = "{course_trace_id}" }}')
        return

    status, body = post_otlp_json(endpoint=args.endpoint, payload=payload)
    if status not in {200, 202, 204}:
        print(body, file=sys.stderr)
        raise SystemExit(f"alloy trace push failed: HTTP {status}")

    print(f"alloy_trace_push_status={status}")
    print(f"trace_preview={output_path}")
    print(f"span_count={span_count}")
    print(f"tempo_trace_id={tempo_trace_id}")
    print(f'traceql={{ .course_trace_id = "{course_trace_id}" }}')
    print("alloy_trace_push_result=ok")


if __name__ == "__main__":
    main()
