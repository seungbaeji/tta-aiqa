"""Kubernetes MLflow tracking server contract for closed-network learners."""

import subprocess
from pathlib import Path

import yaml

ROOT = Path("deploy/kubernetes/base")
KUBERNETES_GUIDE = Path("deploy/kubernetes/README.md")
ROOT_README = Path("README.md")
OFFICIAL_EXPERIMENT = "tta-aiqa-physionet-2012-v2"


def documents(path: str) -> list[dict[str, object]]:
    return [
        item
        for item in yaml.safe_load_all((ROOT / path).read_text(encoding="utf-8"))
        if item
    ]


def overlay_documents(name: str) -> list[dict[str, object]]:
    result = subprocess.run(
        ("kustomize", "build", f"deploy/kubernetes/overlays/{name}"),
        check=True,
        capture_output=True,
        text=True,
    )
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def named_kind(
    rendered: list[dict[str, object]], kind: str, name: str
) -> dict[str, object]:
    matches = [
        item
        for item in rendered
        if item.get("kind") == kind and item.get("metadata", {}).get("name") == name
    ]
    assert matches, f"expected {kind} {name} in render"
    return matches[0]


def test_kustomization_appends_mlflow_resources_only() -> None:
    kustomization = yaml.safe_load((ROOT / "kustomization.yaml").read_text())

    assert kustomization["resources"] == [
        "namespace.yaml",
        "resource-quota.yaml",
        "model-pvc.yaml",
        "risk-api.yaml",
        "risk-api-ingress.yaml",
        "inference-service.yaml",
        "mlflow-pvc.yaml",
        "mlflow.yaml",
        "mlflow-ingress.yaml",
    ]
    assert [item["name"] for item in kustomization["configMapGenerator"]] == [
        "risk-api-config",
        "model-contract",
        "model-identity",
    ]


def test_mlflow_ingress_routes_clusterip_without_hostname() -> None:
    ingress = documents("mlflow-ingress.yaml")[0]
    rule = ingress["spec"]["rules"][0]
    path = rule["http"]["paths"][0]
    backend = path["backend"]["service"]

    assert ingress["kind"] == "Ingress"
    assert ingress["metadata"]["name"] == "mlflow"
    assert ingress["metadata"]["namespace"] == "tta-aiqa"
    assert ingress["metadata"]["labels"]["app.kubernetes.io/name"] == "mlflow"
    assert ingress["spec"]["ingressClassName"] == "traefik"
    assert "host" not in rule
    assert path["path"] == "/"
    assert path["pathType"] == "Prefix"
    assert backend["name"] == "mlflow"
    assert backend["port"]["name"] == "http"
    assert "tls" not in ingress["spec"]


def test_mlflow_service_is_clusterip_named_mlflow() -> None:
    service = next(
        item for item in documents("mlflow.yaml") if item["kind"] == "Service"
    )

    assert service["metadata"]["name"] == "mlflow"
    assert service["metadata"]["namespace"] == "tta-aiqa"
    assert service["spec"].get("type", "ClusterIP") == "ClusterIP"
    assert service["spec"]["selector"] == {"app.kubernetes.io/name": "mlflow"}
    assert service["spec"]["ports"][0]["name"] == "http"
    assert service["spec"]["ports"][0]["port"] == 80
    assert service["spec"]["ports"][0]["targetPort"] == "http"


def test_mlflow_deployment_reuses_model_trainer_image_without_fake_digest() -> None:
    deployment = next(
        item for item in documents("mlflow.yaml") if item["kind"] == "Deployment"
    )
    spec = deployment["spec"]["template"]["spec"]
    container = spec["containers"][0]
    command = container["command"]
    environment = {item["name"]: item["value"] for item in container.get("env", [])}

    assert spec["imagePullSecrets"] == [{"name": "ghcr-pull"}]
    assert container["image"] == "ghcr.io/seungbaeji/tta-aiqa-model-trainer"
    assert "@sha256:" not in container["image"]
    assert command[:2] == ["mlflow", "server"]
    assert "--backend-store-uri" in command
    assert "sqlite:////runtime/mlflow/mlflow.db" in command
    assert "--artifacts-destination" in command
    assert "/runtime/mlflow/artifacts" in command
    assert OFFICIAL_EXPERIMENT not in yaml.safe_dump(deployment)
    assert environment.get("MLFLOW_EXPERIMENT_NAME") != OFFICIAL_EXPERIMENT
    assert "tta-aiqa-physionet-2012-v2" not in yaml.safe_dump(container)


def test_mlflow_pvc_stores_sqlite_and_artifacts() -> None:
    documents_ = documents("mlflow-pvc.yaml")
    volume = next(item for item in documents_ if item["kind"] == "PersistentVolume")
    claim = next(item for item in documents_ if item["kind"] == "PersistentVolumeClaim")
    deployment = next(
        item for item in documents("mlflow.yaml") if item["kind"] == "Deployment"
    )
    spec = deployment["spec"]["template"]["spec"]
    mount = next(
        item
        for item in spec["containers"][0]["volumeMounts"]
        if item["name"] == "mlflow-store"
    )
    volume_source = next(
        item for item in spec["volumes"] if item["name"] == "mlflow-store"
    )

    assert volume["metadata"]["name"] == "course-mlflow"
    assert volume["spec"]["hostPath"]["path"] == "/mnt/course-mlflow"
    assert claim["metadata"]["name"] == "course-mlflow"
    assert claim["metadata"]["namespace"] == "tta-aiqa"
    assert mount["mountPath"] == "/runtime/mlflow"
    assert volume_source["persistentVolumeClaim"]["claimName"] == "course-mlflow"


def test_mlflow_image_and_cluster_verification_are_recorded_as_pending() -> None:
    guide = KUBERNETES_GUIDE.read_text(encoding="utf-8")
    readme = ROOT_README.read_text(encoding="utf-8")
    mlflow_section = readme.split("### 5-3. MLflow 확인", maxsplit=1)[1]
    section = mlflow_section.split("## ", maxsplit=1)[0]

    assert "AIQA_MLFLOW_TRACKING_URI" in guide
    assert "AIQA_MLFLOW_TRACKING_URI" in section
    assert "pending" in guide.lower()
    assert "pending" in section.lower()
    assert "oracle/k3s" in guide
    assert "tta-aiqa" in guide
    assert "ghcr.io/seungbaeji/tta-aiqa-model-trainer" in guide
    assert "apps/model-trainer/Dockerfile" in guide
    assert "http://127.0.0.1:5000" in section
    assert "닫힌망 기본 경로가 아닙니다" in section
    assert 'if [ -z "${TARGET_CONTEXT:-}" ]' in guide
    assert 'CURRENT_CONTEXT="$(kubectl config current-context)"' in guide


def test_baseline_overlay_renders_mlflow_ingress_without_hostname() -> None:
    ingress = named_kind(overlay_documents("baseline"), "Ingress", "mlflow")
    rule = ingress["spec"]["rules"][0]
    backend = rule["http"]["paths"][0]["backend"]["service"]

    assert ingress["spec"]["ingressClassName"] == "traefik"
    assert "host" not in rule
    assert rule["http"]["paths"][0]["path"] == "/"
    assert backend["name"] == "mlflow"
    assert backend["port"]["name"] == "http"


def test_candidate_and_rollback_overlays_inherit_mlflow_ingress() -> None:
    for name in ("candidate-b", "rollback"):
        ingress = named_kind(overlay_documents(name), "Ingress", "mlflow")
        rule = ingress["spec"]["rules"][0]
        backend = rule["http"]["paths"][0]["backend"]["service"]

        assert ingress["metadata"]["namespace"] == "tta-aiqa"
        assert ingress["spec"]["ingressClassName"] == "traefik"
        assert "host" not in rule
        assert backend["name"] == "mlflow"
        assert backend["port"]["name"] == "http"
