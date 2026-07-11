"""Logging and Prometheus adapters for API telemetry."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

from aiqa_observability.domain import PredictionObservation, TelemetryContract


class JsonTelemetryFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        document: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        fields = getattr(record, "aiqa_fields", None)
        if isinstance(fields, dict):
            document.update(fields)
        return json.dumps(document, separators=(",", ":"), sort_keys=True)


class TelemetryRuntime:
    def __init__(self, contract: TelemetryContract, environment: str) -> None:
        self.contract = contract
        self.environment = environment
        self.registry = CollectorRegistry()
        service = ["service_name", "environment"]
        self._requests = Counter(
            contract.metrics.request_count,
            "Risk API HTTP requests",
            [*service, "route", "method", "status_code"],
            registry=self.registry,
        )
        self._latency = Histogram(
            contract.metrics.request_latency,
            "Risk API HTTP request duration",
            [*service, "route", "method", "status_code"],
            registry=self.registry,
        )
        prediction_labels = [
            *service,
            "model_profile",
            "model_version",
            "scenario",
            "prediction",
        ]
        self._predictions = Counter(
            contract.metrics.prediction_count,
            "Mortality risk predictions",
            prediction_labels,
            registry=self.registry,
        )
        self._scores = Histogram(
            contract.metrics.score,
            "Predicted mortality risk score",
            prediction_labels,
            buckets=(0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.9, 1.0),
            registry=self.registry,
        )
        self._missing = Histogram(
            contract.metrics.missing_features,
            "Missing model input feature count",
            prediction_labels,
            buckets=(0, 1, 2, 5, 10, 20, 50, 100, 150),
            registry=self.registry,
        )
        self._logger = _build_logger()

    def record_prediction(self, event: PredictionObservation) -> None:
        labels = self._prediction_labels(event)
        self._predictions.labels(**labels).inc()
        self._scores.labels(**labels).observe(event.score)
        self._missing.labels(**labels).observe(event.missing_feature_count)
        self._logger.info(
            "risk_prediction",
            extra={
                "aiqa_fields": {
                    "event": "risk_prediction",
                    "service_name": self.contract.service_name,
                    "service_namespace": self.contract.service_namespace,
                    "environment": self.environment,
                    **asdict(event),
                }
            },
        )

    def observe_request(
        self,
        *,
        request_id: str,
        route: str,
        method: str,
        status_code: int,
        duration_seconds: float,
        scenario: str,
        trace_id: str,
    ) -> None:
        labels = {
            "service_name": self.contract.service_name,
            "environment": self.environment,
            "route": route,
            "method": method,
            "status_code": str(status_code),
        }
        self._requests.labels(**labels).inc()
        self._latency.labels(**labels).observe(duration_seconds)
        self._logger.info(
            "http_request",
            extra={
                "aiqa_fields": {
                    "event": "http_request",
                    "service_name": self.contract.service_name,
                    "service_namespace": self.contract.service_namespace,
                    "environment": self.environment,
                    "request_id": request_id,
                    "scenario": scenario,
                    "trace_id": trace_id,
                    "route": route,
                    "method": method,
                    "status_code": status_code,
                    "duration_seconds": round(duration_seconds, 6),
                }
            },
        )

    def render_metrics(self) -> bytes:
        return generate_latest(self.registry)

    @staticmethod
    def clock() -> float:
        return time.perf_counter()

    def _prediction_labels(self, event: PredictionObservation) -> dict[str, str]:
        return {
            "service_name": self.contract.service_name,
            "environment": self.environment,
            "model_profile": event.model_profile,
            "model_version": event.model_version,
            "scenario": event.scenario,
            "prediction": event.prediction,
        }


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("aiqa.telemetry")
    logger.setLevel(logging.INFO)
    if not any(getattr(handler, "aiqa_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonTelemetryFormatter())
        handler.aiqa_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.propagate = False
    return logger
