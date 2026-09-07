"""Compose topology and security contract tests."""

import json
import re
from pathlib import Path

import yaml
from traffic_generator.adapters import load_traffic_config


def compose() -> dict[str, object]:
    return yaml.safe_load(
        Path("deploy/compose.yaml").read_text(encoding="utf-8")
    )


def test_compose_runs_same_local_risk_api_and_independent_traffic_app() -> None:
    services = compose()["services"]
    images = json.loads(
        Path(
            "docs/evidence/deployment/runtime-images-v2-20260908-23fbb5d.json"
        ).read_text(
            encoding="utf-8"
        )
    )["images"]

    assert set(services) == {"mlflow", "risk-api", "traffic-generator"}
    assert services["risk-api"]["image"] == images["risk_api"]["reference"]
    assert services["risk-api"]["build"]["dockerfile"] == "apps/risk_api/Dockerfile"
    assert services["risk-api"]["environment"]["AIQA_API_MODEL_BACKEND"] == "local"
    assert services["traffic-generator"]["profiles"] == ["traffic"]
    assert services["traffic-generator"]["environment"]["AIQA_TRAFFIC_API_URL"] == (
        "http://risk-api:8000"
    )
    assert (
        services["traffic-generator"]["environment"][
            "AIQA_TRAFFIC_TELEMETRY_CONFIG_PATH"
        ]
        == "/runtime/configs/observability/telemetry.yaml"
    )
    assert (
        services["traffic-generator"]["environment"][
            "AIQA_TRAFFIC_RESPONSE_ARTIFACT_PATH"
        ]
        == "/runtime/artifacts/traffic/compose.jsonl"
    )
    assert (
        services["traffic-generator"]["environment"][
            "AIQA_TRAFFIC_PORTABLE_RESPONSE_ARTIFACT_PATH"
        ]
        == "artifacts/traffic/compose.jsonl"
    )
    assert (
        services["traffic-generator"]["environment"][
            "AIQA_TRAFFIC_PORTABLE_MANIFEST_PATH"
        ]
        == "artifacts/traffic/collection-session.json"
    )


def test_compose_excludes_monitoring_servers_and_mounts_secrets_read_only() -> None:
    document = compose()
    serialized = yaml.safe_dump(document).lower()

    assert all(
        name not in document["services"]
        for name in ("grafana", "loki", "tempo", "prometheus")
    )
    assert "/var/run/secrets/aiqa/risk-api:ro" in serialized
    assert "/var/run/secrets/aiqa/traffic-generator:ro" in serialized


def test_compose_published_ports_default_to_loopback_with_explicit_override() -> None:
    services = compose()["services"]
    override = yaml.safe_load(
        Path("deploy/compose.grafana-cloud.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert services["mlflow"]["ports"] == [
        "0.0.0.0:${AIQA_MLFLOW_BIND_PORT:-5000}:5000"
    ]
    assert services["mlflow"]["command"] == [
        "mlflow",
        "server",
        "--backend-store-uri",
        "sqlite:////runtime/mlflow/mlflow.db",
        "--artifacts-destination",
        "/runtime/mlflow/artifacts",
        "--host",
        "0.0.0.0",
        "--port",
        "5000",
        "--allowed-hosts",
        "*",
        "--workers",
        "1",
    ]
    assert services["risk-api"]["ports"] == [
        "${AIQA_COMPOSE_BIND_HOST:-127.0.0.1}:8000:8000"
    ]
    assert override["services"]["alloy"]["ports"] == [
        "${AIQA_COMPOSE_BIND_HOST:-127.0.0.1}:12345:12345"
    ]


def test_compose_mlflow_documents_npm_public_host() -> None:
    text = Path("deploy/compose.yaml").read_text(encoding="utf-8")
    mlflow_block = text.split("  risk-api:", maxsplit=1)[0]

    assert "Nginx Proxy Manager" in mlflow_block
    assert "mlflow-ttaN-pveX.apps.learn.mrml.dev" in mlflow_block
    assert ":5000" in mlflow_block
    assert "AIQA_MLFLOW_TRACKING_URI" in mlflow_block
    assert "http://127.0.0.1:5000" in mlflow_block


def test_grafana_cloud_override_adds_only_alloy_collector() -> None:
    override = yaml.safe_load(
        Path("deploy/compose.grafana-cloud.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert set(override["services"]) == {"risk-api", "traffic-generator", "alloy"}
    assert override["services"]["alloy"]["image"] == (
        "grafana/alloy@sha256:51aeb9d829239345070619dad3edd6873186f913c84f45b365b74574fcb38ec0"
    )
    assert (
        override["services"]["traffic-generator"]["environment"][
            "AIQA_TRAFFIC_OTLP_ENDPOINT"
        ]
        == "http://alloy:4318"
    )
    assert all(
        name not in override["services"]
        for name in ("grafana", "loki", "tempo", "prometheus")
    )
    assert override["services"]["alloy"]["read_only"] is True


def test_grafana_cloud_override_routes_both_apps_through_alloy_otlp() -> None:
    override = yaml.safe_load(
        Path("deploy/compose.grafana-cloud.yaml").read_text(
            encoding="utf-8"
        )
    )
    alloy = Path("deploy/alloy/config.alloy").read_text(
        encoding="utf-8"
    )

    assert (
        override["services"]["risk-api"]["environment"]["AIQA_API_OTLP_ENDPOINT"]
        == "http://alloy:4318"
    )
    assert (
        override["services"]["traffic-generator"]["environment"][
            "AIQA_TRAFFIC_OTLP_ENDPOINT"
        ]
        == "http://alloy:4318"
    )
    assert 'otelcol.receiver.otlp "aiqa"' in alloy
    assert 'endpoint = "0.0.0.0:4318"' in alloy
    assert "traces = [otelcol.processor.batch.aiqa.input]" in alloy
    assert "traces = [otelcol.exporter.otlphttp.grafana_cloud.input]" in alloy
    assert "username = string.trim_space(local.file.otlp_username.content)" in alloy
    assert "password = local.file.api_key.content" in alloy
    assert "client_auth" not in alloy


def test_course_traffic_spans_two_scrapes_and_waits_for_collection() -> None:
    """Each scenario must yield two metric samples learners can compare."""
    alloy = Path("deploy/alloy/config.alloy").read_text(
        encoding="utf-8"
    )
    match = re.search(r'scrape_interval = "([0-9]+)s"', alloy)
    assert match is not None
    scrape_interval = float(match.group(1))
    plans = load_traffic_config(Path("configs/traffic/scenarios.yaml")).plans()

    assert all(
        (plan.request_count - 1) * plan.interval_seconds > scrape_interval
        for plan in plans.values()
    )
    assert all(
        plan.collection_wait_seconds > scrape_interval for plan in plans.values()
    )
