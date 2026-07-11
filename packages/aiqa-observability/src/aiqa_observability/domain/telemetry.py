"""Technology-independent telemetry contracts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricNames:
    request_count: str
    request_latency: str
    prediction_count: str
    score: str
    missing_features: str


@dataclass(frozen=True)
class TelemetryLabels:
    resource: tuple[str, ...]
    request_metrics: tuple[str, ...]
    prediction_metrics: tuple[str, ...]
    logs_and_traces: tuple[str, ...]


@dataclass(frozen=True)
class TelemetryContract:
    schema_version: int
    service_name: str
    service_namespace: str
    environment: str
    labels: TelemetryLabels
    metrics: MetricNames

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("telemetry schema version must be positive")
        if not self.service_name or not self.service_namespace:
            raise ValueError("telemetry service identity is required")
        metric_names = tuple(vars(self.metrics).values())
        if len(metric_names) != len(set(metric_names)):
            raise ValueError("telemetry metric names must be unique")
        if "request_id" in self.labels.request_metrics:
            raise ValueError("request_id is forbidden as a metric label")
        if "request_id" in self.labels.prediction_metrics:
            raise ValueError("request_id is forbidden as a metric label")


@dataclass(frozen=True)
class PredictionObservation:
    request_id: str
    model_profile: str
    model_version: str
    score: float
    threshold: float
    prediction: str
    missing_feature_count: int
    scenario: str
    trace_id: str = ""
