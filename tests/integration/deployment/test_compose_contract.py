"""Compose topology and security contract tests."""

from pathlib import Path

import yaml


def compose() -> dict[str, object]:
    return yaml.safe_load(
        Path("deploy/compose/simple-mlops/compose.yaml").read_text(encoding="utf-8")
    )


def test_compose_runs_same_local_risk_api_and_independent_traffic_app() -> None:
    services = compose()["services"]

    assert set(services) == {"mlflow", "risk-api", "traffic-generator"}
    assert services["risk-api"]["environment"]["AIQA_API_MODEL_BACKEND"] == "local"
    assert services["traffic-generator"]["profiles"] == ["traffic"]
    assert services["traffic-generator"]["environment"]["AIQA_TRAFFIC_API_URL"] == (
        "http://risk-api:8000"
    )
    assert services["traffic-generator"]["environment"][
        "AIQA_TRAFFIC_TELEMETRY_CONFIG_PATH"
    ] == "/runtime/configs/observability/telemetry.yaml"


def test_compose_excludes_monitoring_servers_and_mounts_secrets_read_only() -> None:
    document = compose()
    serialized = yaml.safe_dump(document).lower()

    assert all(
        name not in document["services"]
        for name in ("grafana", "loki", "tempo", "prometheus")
    )
    assert "/var/run/secrets/aiqa/risk-api:ro" in serialized
    assert "/var/run/secrets/aiqa/traffic-generator:ro" in serialized


def test_grafana_cloud_override_adds_only_alloy_collector() -> None:
    override = yaml.safe_load(
        Path("deploy/compose/simple-mlops/compose.grafana-cloud.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert set(override["services"]) == {"risk-api", "traffic-generator", "alloy"}
    assert override["services"]["alloy"]["image"] == "grafana/alloy:v1.16.1"
    assert override["services"]["traffic-generator"]["environment"][
        "AIQA_TRAFFIC_OTLP_ENDPOINT"
    ] == "http://alloy:4318"
    assert all(
        name not in override["services"]
        for name in ("grafana", "loki", "tempo", "prometheus")
    )
    assert override["services"]["alloy"]["read_only"] is True
