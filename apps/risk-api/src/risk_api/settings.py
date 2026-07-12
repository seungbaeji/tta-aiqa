"""Runtime settings for the Risk API process."""

from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RiskApiSettings(BaseSettings):
    """Validate app-specific runtime settings and model backend requirements."""

    model_config = SettingsConfigDict(
        env_prefix="AIQA_API_",
        env_file=".env.risk-api",
        env_file_encoding="utf-8",
        secrets_dir="/var/run/secrets/aiqa/risk-api",
        extra="forbid",
    )

    environment: str = "local"
    port: int = Field(default=8000, ge=1, le=65535)
    model_backend: Literal["local", "kserve"]
    api_config_path: Path
    feature_contract_path: Path
    telemetry_config_path: Path
    otlp_endpoint: AnyHttpUrl | None = None
    model_bundle_path: Path | None = None
    kserve_url: AnyHttpUrl | None = None
    kserve_model_name: str | None = None
    model_metadata_path: Path | None = None

    @model_validator(mode="after")
    def validate_backend_location(self) -> "RiskApiSettings":
        """Require exactly the backend-specific locations needed at process startup."""
        if self.model_backend == "local" and self.model_bundle_path is None:
            raise ValueError("local model backend requires model_bundle_path")
        if self.model_backend == "kserve" and self.kserve_url is None:
            raise ValueError("kserve model backend requires kserve_url")
        if self.model_backend == "kserve" and not self.kserve_model_name:
            raise ValueError("kserve model backend requires kserve_model_name")
        if self.model_backend == "kserve" and self.model_metadata_path is None:
            raise ValueError("kserve model backend requires model_metadata_path")
        return self
