"""Process-lifetime telemetry resource identity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TelemetryResource:
    """Process-lifetime identity carried by every emitted signal."""

    service_name: str
    service_namespace: str
    environment: str

    def __post_init__(self) -> None:
        identifiers = (self.service_name, self.service_namespace, self.environment)
        if any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in identifiers
        ):
            raise ValueError(
                "telemetry resource identity must contain non-empty trimmed strings"
            )

    def as_log_fields(self) -> dict[str, str]:
        """Return the stable structured-log representation of this resource."""
        return {
            "service_name": self.service_name,
            "service_namespace": self.service_namespace,
            "environment": self.environment,
        }

    def as_trace_attributes(self) -> dict[str, str]:
        """Return OpenTelemetry resource attributes for this process."""
        return {
            "service.name": self.service_name,
            "service.namespace": self.service_namespace,
            "deployment.environment.name": self.environment,
        }
