"""App-owned runtime and secret injection contracts."""

from pathlib import Path

from grafana_dashboard_importer.settings import GrafanaDashboardSettings
from kserve_predictor.settings import KServePredictorSettings
from pydantic import ValidationError
from risk_api.settings import RiskApiSettings


def test_apps_use_distinct_environment_prefixes_and_secret_directories() -> None:
    assert RiskApiSettings.model_config["env_prefix"] == "AIQA_API_"
    assert RiskApiSettings.model_config["env_file"] == ".env.risk-api"
    assert RiskApiSettings.model_config["secrets_dir"] == (
        "/var/run/secrets/aiqa/risk-api"
    )
    assert GrafanaDashboardSettings.model_config["env_prefix"] == "AIQA_GRAFANA_"
    assert GrafanaDashboardSettings.model_config["env_file"] == ".env.grafanacloud"
    assert GrafanaDashboardSettings.model_config["secrets_dir"] == (
        "/var/run/secrets/aiqa/grafana-dashboard-importer"
    )


def test_local_backend_requires_local_model_bundle(tmp_path: Path) -> None:
    try:
        RiskApiSettings(
            _secrets_dir=tmp_path,
            model_backend="local",
            api_config_path="api.yaml",
            feature_contract_path="feature.yaml",
            telemetry_config_path="telemetry.yaml",
        )
    except ValidationError as error:
        assert "local model backend requires model_bundle_path" in str(error)
    else:
        raise AssertionError("missing local model bundle must be rejected")


def test_kserve_backend_requires_endpoint(tmp_path: Path) -> None:
    try:
        RiskApiSettings(
            _secrets_dir=tmp_path,
            model_backend="kserve",
            api_config_path="api.yaml",
            feature_contract_path="feature.yaml",
            telemetry_config_path="telemetry.yaml",
        )
    except ValidationError as error:
        assert "kserve model backend requires kserve_url" in str(error)
    else:
        raise AssertionError("missing KServe endpoint must be rejected")


def test_kserve_predictor_rejects_invalid_service_port(tmp_path: Path) -> None:
    """The predictor runtime setting rejects ports outside the TCP range."""
    try:
        KServePredictorSettings(
            _secrets_dir=tmp_path,
            model_bundle_path="model.joblib",
            feature_contract_path="contract.yaml",
            port=0,
        )
    except ValidationError as error:
        assert "greater than or equal to 1" in str(error)
    else:
        raise AssertionError("invalid KServe predictor port must be rejected")
