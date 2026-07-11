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

    assert service["kind"] == "InferenceService"
    assert service["metadata"]["annotations"]["serving.kserve.io/deploymentMode"] == (
        "RawDeployment"
    )
    assert "baseline-f2576f12512a" in serialized
    assert "candidate-a" not in serialized
    assert container["command"] == ["aiqa-kserve-model"]


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
