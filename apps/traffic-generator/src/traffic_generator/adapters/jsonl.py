"""Append-only JSONL traffic response evidence adapter."""

import json
from dataclasses import asdict
from pathlib import Path

from traffic_generator.domain import TrafficResponse


class JsonlTrafficRecorder:
    """Append traffic response evidence to one JSONL artifact path."""

    def __init__(self, path: Path) -> None:
        """Bind the append-only artifact location for this traffic process."""
        self._path = path

    def record(self, response: TrafficResponse) -> None:
        """Append one serialized response record without rewriting earlier evidence."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(asdict(response), sort_keys=True) + "\n")
