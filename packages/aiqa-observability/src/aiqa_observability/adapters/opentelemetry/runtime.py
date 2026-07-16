"""OpenTelemetry SDK and OTLP trace exporter implementation."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from aiqa_observability.adapters.opentelemetry.endpoint import (
    normalize_traces_endpoint,
)
from aiqa_observability.domain import TelemetryAttributes, TelemetryResource


class TracingRuntime:
    """Own one process-local OpenTelemetry provider and tracer lifecycle."""

    def __init__(
        self,
        resource: TelemetryResource,
        *,
        endpoint: str | None,
    ) -> None:
        """Create a provider and optional OTLP exporter for one process resource."""
        self._closed = False
        self._provider = TracerProvider(
            resource=Resource.create(resource.as_trace_attributes())
        )
        if endpoint is not None:
            self._provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=normalize_traces_endpoint(endpoint))
                )
            )
        self._tracer = self._provider.get_tracer(resource.service_name)

    @property
    def provider(self) -> TracerProvider:
        """Return the explicit provider for framework instrumentation wiring."""
        return self._provider

    @contextmanager
    def span(
        self, name: str, attributes: TelemetryAttributes | None = None
    ) -> Iterator[None]:
        """Create one child span and mark exceptions on it."""
        with self._tracer.start_as_current_span(name) as span:
            self.set_current_attributes(attributes)
            try:
                yield
            except Exception as error:
                span.record_exception(error)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                raise

    def set_current_attributes(self, attributes: TelemetryAttributes | None) -> None:
        """Attach application context to the active span when it is recording."""
        if attributes is None:
            return
        span = trace.get_current_span()
        if span.is_recording():
            for name, value in attributes.items():
                span.set_attribute(f"aiqa.{name}", value)

    def add_event(
        self, name: str, attributes: TelemetryAttributes | None = None
    ) -> None:
        """Add a structured event to the active process-local trace span."""
        span = trace.get_current_span()
        if span.is_recording():
            span.add_event(name, attributes=attributes)

    def current_ids(self) -> tuple[str | None, str | None]:
        """Return active trace and span IDs without creating a metric label."""
        context = trace.get_current_span().get_span_context()
        if not context.is_valid:
            return None, None
        return f"{context.trace_id:032x}", f"{context.span_id:016x}"

    def outbound_headers(self) -> dict[str, str]:
        """Inject the active W3C trace context into a new HTTP header mapping."""
        headers: dict[str, str] = {}
        propagate.inject(headers)
        return headers

    def shutdown(self) -> None:
        """Flush and close this process-local provider at application shutdown."""
        if not self._closed:
            self._provider.force_flush()
            self._provider.shutdown()
            self._closed = True
