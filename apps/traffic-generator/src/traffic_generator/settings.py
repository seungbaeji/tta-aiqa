"""Runtime settings for the Traffic Generator process."""

from pathlib import Path

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class TrafficSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIQA_TRAFFIC_",
        env_file=".env.traffic-generator",
        env_file_encoding="utf-8",
        secrets_dir="/var/run/secrets/aiqa/traffic-generator",
        extra="forbid",
    )

    environment: str = "local"
    telemetry_config_path: Path = Path("configs/observability/telemetry.yaml")
    otlp_endpoint: AnyHttpUrl | None = None
    api_url: AnyHttpUrl
    scenarios_path: Path
    feature_contract_path: Path
    patient_pool_path: Path
    response_artifact_path: Path
