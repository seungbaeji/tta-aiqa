"""JSONL prediction event sink."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_quality.serving.domain.prediction_response import PredictionResponse


@dataclass(frozen=True)
class JsonPredictionEventSink:
    """Append prediction events to a JSONL file."""

    output_path: Path

    def record(self, response: PredictionResponse) -> None:
        """Record one prediction response."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(response.to_dict(), ensure_ascii=False) + "\n")
