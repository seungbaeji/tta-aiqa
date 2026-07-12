"""Validated external DTOs for telemetry policy YAML documents."""

from pydantic import BaseModel, ConfigDict, Field

from aiqa_observability.domain import TelemetryLogLevel, TelemetryPolicy


class LoggingDocument(BaseModel):
    """Shared process-level logging policy in external YAML form."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    level: TelemetryLogLevel


class TelemetryPolicyDocument(BaseModel):
    """Root DTO for one versioned shared telemetry policy document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    service_namespace: str
    logging: LoggingDocument

    def to_domain(self) -> TelemetryPolicy:
        """Convert validated YAML values into an immutable platform policy."""
        return TelemetryPolicy(
            schema_version=self.schema_version,
            service_namespace=self.service_namespace,
            log_level=self.logging.level,
        )
