"""Runtime settings for the KServe predictor process."""

from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KServePredictorSettings(BaseSettings):
    """Validate environment and Secret-backed predictor runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="AIQA_KSERVE_",
        env_file=".env.kserve-predictor",
        env_file_encoding="utf-8",
        secrets_dir="/var/run/secrets/aiqa/kserve-predictor",
        extra="forbid",
    )

    model_name: str = Field(default="mortality-risk", min_length=1)
    port: int = Field(default=8080, ge=1, le=65535)
    environment: str = "local"
    telemetry_config_path: Path = Path("configs/observability/telemetry.yaml")
    otlp_endpoint: AnyHttpUrl | None = None
    model_bundle_path: Path
    feature_contract_path: Path
    expected_model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
