"""Stdlib JSON logging implementation for the observability platform."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

from aiqa_observability.domain import (
    TelemetryContext,
    TelemetryEvent,
    TelemetryResource,
)


class JsonTelemetryFormatter(logging.Formatter):
    """Render platform events as one JSON document per output line."""

    def format(self, record: logging.LogRecord) -> str:
        document: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        fields = getattr(record, "aiqa_fields", None)
        if isinstance(fields, dict):
            document.update(fields)
        return json.dumps(document, separators=(",", ":"), sort_keys=True)


class StructuredLogger:
    """Emit resource and execution context through one stdlib logger."""

    def __init__(
        self,
        resource: TelemetryResource,
        *,
        level: str,
        stream: TextIO | None = None,
    ) -> None:
        self._resource = resource
        self._logger = logging.getLogger(f"aiqa.{resource.service_name}.{id(self)}")
        self._logger.setLevel(getattr(logging, level))
        self._logger.propagate = False
        self._handler = logging.StreamHandler(stream or sys.stderr)
        self._handler.setFormatter(JsonTelemetryFormatter())
        self._logger.addHandler(self._handler)

    def emit(
        self,
        event: TelemetryEvent,
        *,
        context: TelemetryContext | None,
        trace_id: str | None,
        span_id: str | None,
        level: int = logging.INFO,
    ) -> None:
        """Write one correlated JSON event."""
        fields: dict[str, Any] = {
            "event": event.name,
            **self._resource.as_log_fields(),
        }
        if context is not None:
            fields.update(context.as_log_fields())
        if trace_id is not None:
            fields["trace_id"] = trace_id
        if span_id is not None:
            fields["span_id"] = span_id
        fields.update(event.as_fields())
        self._logger.log(level, event.name, extra={"aiqa_fields": fields})

    def close(self) -> None:
        """Detach and close the process-local handler during telemetry shutdown."""
        self._logger.removeHandler(self._handler)
        self._handler.close()
