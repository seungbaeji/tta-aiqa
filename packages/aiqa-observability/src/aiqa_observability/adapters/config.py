"""YAML adapter for the shared telemetry contract."""

from pathlib import Path
from typing import Any

import yaml

from aiqa_observability.domain import MetricNames, TelemetryContract, TelemetryLabels


def load_telemetry_contract(path: Path) -> TelemetryContract:
    document: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("telemetry config root must be a mapping")
    labels = document.get("labels")
    metrics = document.get("metrics")
    if not isinstance(labels, dict) or not isinstance(metrics, dict):
        raise ValueError("telemetry labels and metrics must be mappings")
    return TelemetryContract(
        schema_version=int(document["schema_version"]),
        service_name=str(document["service_name"]),
        service_namespace=str(document["service_namespace"]),
        environment=str(document["environment"]),
        labels=TelemetryLabels(
            resource=tuple(labels["resource"]),
            request_metrics=tuple(labels["request_metrics"]),
            prediction_metrics=tuple(labels["prediction_metrics"]),
            logs_and_traces=tuple(labels["logs_and_traces"]),
        ),
        metrics=MetricNames(**metrics),
    )
