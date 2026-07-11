"""Runtime settings for the Grafana Cloud Dashboard Importer."""

from pathlib import Path

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GrafanaDashboardSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIQA_GRAFANA_",
        env_file=".env.grafanacloud",
        env_file_encoding="utf-8",
        secrets_dir="/var/run/secrets/aiqa/grafana-dashboard-importer",
        extra="forbid",
    )

    url: AnyHttpUrl
    dashboard_path: Path
    dashboard_token: SecretStr
    folder_uid: str
    metrics_datasource_uid: str
    logs_datasource_uid: str
    traces_datasource_uid: str
