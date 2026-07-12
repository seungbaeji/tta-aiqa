"""Kubernetes, KServe, secret, and Alloy deployment contracts."""

from pathlib import Path

import yaml

ROOT = Path("deploy/kubernetes/base")
ALLOY = Path("deploy/kubernetes/components/alloy")


def documents(path: str, root: Path = ROOT) -> list[dict[str, object]]:
    return [
        item
        for item in yaml.safe_load_all((root / path).read_text(encoding="utf-8"))
        if item
    ]


def test_risk_api_uses_internal_kserve_and_read_only_secret_volume() -> None:
    deployment = documents("risk-api.yaml")[0]
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item["value"] for item in container["env"]}

    assert environment["AIQA_API_MODEL_BACKEND"] == "kserve"
    assert "mortality-risk-predictor" in environment["AIQA_API_KSERVE_URL"]
    secret_mount = next(
        item
        for item in container["volumeMounts"]
        if item["name"] == "runtime-secrets"
    )
    assert secret_mount["readOnly"] is True
    assert secret_mount["mountPath"] == "/var/run/secrets/aiqa/risk-api"


def test_base_starts_with_baseline_model() -> None:
    service = documents("inference-service.yaml")[0]
    serialized = yaml.safe_dump(service)
    container = service["spec"]["predictor"]["containers"][0]
    environment = {item["name"]: item["value"] for item in container["env"]}

    assert service["kind"] == "InferenceService"
    assert service["metadata"]["annotations"]["serving.kserve.io/deploymentMode"] == (
        "RawDeployment"
    )
    assert "baseline-f2576f12512a" in serialized
    assert "candidate-a" not in serialized
    assert container["image"] == "ghcr.io/seungbaeji/tta-aiqa-kserve-predictor:v2"
    assert container["command"] == ["aiqa-kserve-predictor"]
    predictor_secrets = next(
        item
        for item in service["spec"]["predictor"]["volumes"]
        if item["name"] == "runtime-secrets"
    )
    assert predictor_secrets["projected"]["sources"][0]["secret"]["name"] == (
        "kserve-predictor-runtime"
    )
    assert environment["AIQA_KSERVE_TELEMETRY_CONFIG_PATH"] == (
        "/runtime/config/telemetry.yaml"
    )
    assert environment["AIQA_KSERVE_OTLP_ENDPOINT"] == (
        "http://alloy.tta-aiqa.svc.cluster.local:4318"
    )
    assert service["spec"]["predictor"]["labels"]["app.kubernetes.io/part-of"] == (
        "tta-aiqa"
    )


def test_kubernetes_deploys_alloy_but_no_monitoring_backend() -> None:
    manifests = "\n".join(
        path.read_text(encoding="utf-8") for path in ALLOY.glob("*.yaml")
    ).lower()
    alloy = documents("alloy.yaml", ALLOY)[0]
    container = alloy["spec"]["template"]["spec"]["containers"][0]

    assert "grafana/alloy:v1.16.1" in manifests
    assert all(
        f"name: {name}\n" not in manifests
        for name in ("grafana", "loki", "tempo", "prometheus")
    )
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False


def test_alloy_collects_all_aiqa_workload_logs_and_otlp_traces() -> None:
    config = (ALLOY / "config/config.alloy").read_text(encoding="utf-8")

    assert 'discovery.relabel "aiqa_logs"' in config
    assert "__meta_kubernetes_pod_label_app_kubernetes_io_part_of" in config
    assert 'regex         = "tta-aiqa"' in config
    assert 'regex         = "alloy"' in config
    assert 'otelcol.receiver.otlp "aiqa"' in config
    assert 'otelcol.processor.batch "aiqa"' in config


def test_candidate_and_rollback_overlays_select_only_approved_models() -> None:
    candidate = Path(
        "deploy/kubernetes/overlays/candidate-b/kustomization.yaml"
    ).read_text(encoding="utf-8")
    rollback = Path(
        "deploy/kubernetes/overlays/rollback/kustomization.yaml"
    ).read_text(encoding="utf-8")

    assert "candidate-b-c712a8e52344" in candidate
    assert "candidate-a" not in candidate
    assert "baseline-f2576f12512a" in rollback


def test_deployment_config_copies_match_canonical_config() -> None:
    pairs = {
        "config/api.yaml": "configs/serving/api.yaml",
        "config/model-input.yaml": "configs/contracts/model-input.yaml",
        "config/telemetry.yaml": "configs/observability/telemetry.yaml",
    }
    for deployed, canonical in pairs.items():
        assert yaml.safe_load((ROOT / deployed).read_text()) == yaml.safe_load(
            Path(canonical).read_text()
        )

    kustomization = yaml.safe_load((ROOT / "kustomization.yaml").read_text())
    model_contract = next(
        item
        for item in kustomization["configMapGenerator"]
        if item["name"] == "model-contract"
    )
    assert "telemetry.yaml=config/telemetry.yaml" in model_contract["files"]
