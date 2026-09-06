"""Shared process-level telemetry policy values."""

from dataclasses import dataclass
from enum import StrEnum


class TelemetryLogLevel(StrEnum):
    """Structured log levels allowed in the shared telemetry policy."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class TelemetryPolicy:
    """Versioned policy shared by every AIQA Python process."""

    schema_version: int
    service_namespace: str
    log_level: TelemetryLogLevel

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version < 1
        ):
            raise ValueError("telemetry schema version must be a positive integer")
        if (
            not isinstance(self.service_namespace, str)
            or not self.service_namespace
            or self.service_namespace != self.service_namespace.strip()
        ):
            raise ValueError(
                "telemetry service namespace must be a non-empty trimmed string"
            )
        if not isinstance(self.log_level, TelemetryLogLevel):
            raise ValueError("telemetry log level must be a TelemetryLogLevel")
