"""Prediction event recorder adapters."""

import logging
from dataclasses import asdict

from aiqa_serving.domain import PredictionEvent


class StructuredLogEventRecorder:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("aiqa.prediction")

    def record(self, event: PredictionEvent) -> None:
        self._logger.info("risk_prediction", extra={"aiqa_event": asdict(event)})


class InMemoryEventRecorder:
    def __init__(self) -> None:
        self.events: list[PredictionEvent] = []

    def record(self, event: PredictionEvent) -> None:
        self.events.append(event)
