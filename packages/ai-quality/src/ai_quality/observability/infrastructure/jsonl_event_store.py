"""JSONL event store for observability labs."""

from __future__ import annotations

import json
from pathlib import Path

from ai_quality.observability.domain.prediction_event import PredictionEvent


def write_events_jsonl(events: list[PredictionEvent], output_path: Path) -> Path:
    """Write prediction events as JSON lines."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
    return output_path


def read_events_jsonl(input_path: Path) -> list[PredictionEvent]:
    """Read prediction events from JSON lines."""
    events: list[PredictionEvent] = []
    with input_path.open(encoding="utf-8") as file:
        for line in file:
            payload = json.loads(line)
            events.append(PredictionEvent(**payload))
    return events
