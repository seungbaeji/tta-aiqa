"""Public platform API for correlated AIQA application telemetry."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TextIO
from uuid import uuid4

from prometheus_client import Counter, Histogram

from aiqa_observability.adapters.logging import StructuredLogger
from aiqa_observability.adapters.opentelemetry import TracingRuntime
from aiqa_observability.adapters.prometheus import PrometheusMeter
from aiqa_observability.context import bind_context, current_context
from aiqa_observability.domain import (
    MetricSpec,
    TelemetryAttributes,
    TelemetryContext,
    TelemetryEvent,
    TelemetryPolicy,
    TelemetryResource,
)


class Telemetry:
    """One process-local facade for structured logs, traces, and metrics."""

    def __init__(
        self,
        resource: TelemetryResource,
        *,
        policy: TelemetryPolicy,
        otlp_endpoint: str | None,
        log_stream: TextIO | None = None,
    ) -> None:
        self.resource = resource
        self._logger = StructuredLogger(
            resource,
            level=policy.log_level,
            stream=log_stream,
        )
        self.tracing = TracingRuntime(
            resource,
            endpoint=otlp_endpoint,
        )
        self._meter = PrometheusMeter()
        self._closed = False

    @contextmanager
    def request_scope(
        self,
        *,
        request_id: str,
        scenario: str,
        operation: str = "http.request",
        attributes: TelemetryAttributes | None = None,
    ) -> Iterator[TelemetryContext]:
        """Bind HTTP-specific correlation fields without creating a duplicate span."""
        context = self._context(
            operation=operation,
            request_id=request_id,
            scenario=scenario,
            attributes=attributes,
        )
        with bind_context(context):
            self.tracing.set_current_attributes(context.as_log_fields())
            yield context

    @contextmanager
    def run_scope(
        self,
        operation: str,
        *,
        run_id: str | None = None,
        scenario: str | None = None,
        attributes: TelemetryAttributes | None = None,
    ) -> Iterator[TelemetryContext]:
        """Create a root operation for a CLI or batch process run."""
        context = self._context(
            operation=operation,
            run_id=run_id or str(uuid4()),
            scenario=scenario,
            attributes=attributes,
        )
        with bind_context(context), self.tracing.span(
            operation, context.as_log_fields()
        ):
            self.event("operation.started")
            try:
                yield context
            except Exception as error:
                self.event(
                    "operation.failed",
                    level=logging.ERROR,
                    attributes={
                        "error_message": str(error),
                        "error_type": type(error).__name__,
                    },
                )
                raise
            else:
                self.event("operation.completed")

    @contextmanager
    def operation_scope(
        self,
        operation: str,
        *,
        attributes: TelemetryAttributes | None = None,
    ) -> Iterator[TelemetryContext]:
        """Create a child operation under the current request or process run."""
        context = self._context(operation=operation, attributes=attributes)
        with bind_context(context), self.tracing.span(
            operation, context.as_log_fields()
        ):
            yield context

    def event(
        self,
        name: str,
        *,
        attributes: TelemetryAttributes | None = None,
        level: int = logging.INFO,
    ) -> None:
        """Emit one JSON event and attach it to the current trace span."""
        event = TelemetryEvent.create(name, attributes)
        context = current_context()
        trace_id, span_id = self.tracing.current_ids()
        self._logger.emit(
            event,
            context=context,
            trace_id=trace_id,
            span_id=span_id,
            level=level,
        )
        span_attributes = event.as_fields()
        if context is not None:
            span_attributes.update(context.as_log_fields())
        self.tracing.add_event(event.name, span_attributes)
        self.tracing.set_current_attributes(span_attributes)

    def counter(self, spec: MetricSpec) -> Counter:
        """Register one bounded counter owned by the calling application."""
        return self._meter.counter(spec)

    def histogram(self, spec: MetricSpec) -> Histogram:
        """Register one bounded histogram owned by the calling application."""
        return self._meter.histogram(spec)

    def render_metrics(self) -> bytes:
        """Render metrics for a long-running application's scrape endpoint."""
        return self._meter.render()

    def outbound_trace_headers(self) -> dict[str, str]:
        """Return W3C trace headers for an application-owned outbound HTTP call."""
        return self.tracing.outbound_headers()

    def shutdown(self) -> None:
        """Flush trace data and close the log handler at process shutdown."""
        if not self._closed:
            self.tracing.shutdown()
            self._logger.close()
            self._closed = True

    def _context(
        self,
        *,
        operation: str,
        request_id: str | None = None,
        run_id: str | None = None,
        scenario: str | None = None,
        attributes: TelemetryAttributes | None = None,
    ) -> TelemetryContext:
        existing = current_context()
        inherited = dict(existing.attributes) if existing is not None else {}
        if attributes is not None:
            inherited.update(attributes)
        return TelemetryContext.create(
            operation=operation,
            request_id=request_id
            if request_id is not None
            else (existing.request_id if existing is not None else None),
            run_id=(
                run_id
                if run_id is not None
                else (existing.run_id if existing is not None else None)
            ),
            scenario=scenario
            if scenario is not None
            else (existing.scenario if existing is not None else None),
            attributes=inherited,
        )


def create_telemetry(
    *,
    service_name: str,
    environment: str,
    policy: TelemetryPolicy,
    otlp_endpoint: str | None = None,
    log_stream: TextIO | None = None,
) -> Telemetry:
    """Build one platform telemetry facade in an application composition root."""
    return Telemetry(
        TelemetryResource(
            service_name=service_name,
            service_namespace=policy.service_namespace,
            environment=environment,
        ),
        policy=policy,
        otlp_endpoint=otlp_endpoint,
        log_stream=log_stream,
    )
