"""OpenTelemetry adapter configured to export OTLP HTTP spans to Alloy."""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from aiqa_observability.domain import TelemetryContract


def instrument_fastapi(
    app: FastAPI,
    *,
    contract: TelemetryContract,
    environment: str,
    endpoint: str | None,
) -> None:
    if endpoint is None:
        return
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": contract.service_name,
                "service.namespace": contract.service_namespace,
                "deployment.environment.name": environment,
            }
        )
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces")
        )
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
