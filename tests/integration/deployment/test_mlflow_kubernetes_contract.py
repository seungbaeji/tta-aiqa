"""Kubernetes MLflow YAML stays in base but out of overlay apply."""

import subprocess
from pathlib import Path

import yaml

BASE = Path("deploy/k8s/base")
KUBERNETES_GUIDE = Path("deploy/k8s/README.md")
ROOT_README = Path("README.md")
OFFICIAL_EXPERIMENT = "tta-aiqa-physionet-2012-v2"
MLFLOW_RESOURCES = ("mlflow.yaml", "mlflow-pvc.yaml", "mlflow-ingress.yaml")


def documents(path: str, root: Path = BASE) -> list[dict[str, object]]:
    return [
        item
        for item in yaml.safe_load_all((root / path).read_text(encoding="utf-8"))
        if item
    ]


def overlay_documents(name: str) -> list[dict[str, object]]:
    result = subprocess.run(
        ("kustomize", "build", f"deploy/k8s/{name}"),
        check=True,
        capture_output=True,
        text=True,
    )
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def named_kind(
    rendered: list[dict[str, object]], kind: str, name: str
) -> dict[str, object] | None:
    matches = [
        item
        for item in rendered
        if item.get("kind") == kind and item.get("metadata", {}).get("name") == name
    ]
    return matches[0] if matches else None


def test_base_kustomization_does_not_include_mlflow() -> None:
    kustomization_text = (BASE / "kustomization.yaml").read_text(encoding="utf-8")
    kustomization = yaml.safe_load(kustomization_text)

    assert kustomization["resources"] == [
        "namespace.yaml",
        "resource-quota.yaml",
        "model-pvc.yaml",
        "risk-api.yaml",
        "risk-api-ingress.yaml",
        "inference-service.yaml",
    ]
    for name in MLFLOW_RESOURCES:
        assert (BASE / name).is_file()
        assert name not in kustomization["resources"]
        assert name in kustomization_text
        assert f"# - {name}" in kustomization_text


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
    assert "--allowed-hosts" in command
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


def test_classroom_mlflow_is_compose_and_k8s_yaml_is_unapplied_reference() -> None:
    guide = KUBERNETES_GUIDE.read_text(encoding="utf-8")
    readme = ROOT_README.read_text(encoding="utf-8")
    mlflow_section = readme.split("### 5-3. MLflow 확인", maxsplit=1)[1]
    section = mlflow_section.split("## ", maxsplit=1)[0]
    compose = Path("deploy/compose.yaml").read_text(
        encoding="utf-8"
    )

    assert "mlflow.yaml" in guide
    assert "kustomization.yaml" in guide
    assert "AIQA_MLFLOW_TRACKING_URI" in guide
    assert "student-development-tracking" in guide
    assert "labs/run/log_development.py" in guide
    assert "AIQA_MLFLOW_TRACKING_URI" in section
    assert "0.0.0.0:${AIQA_MLFLOW_BIND_PORT:-5000}:5000" in compose
    assert "--allowed-hosts" in compose
    assert "http://127.0.0.1:5000" in section
    assert "닫힌망 기본 경로가 아닙니다" in section
    assert "deploy/k8s/base/mlflow.yaml" in section
    assert 'if [ -z "${TARGET_CONTEXT:-}" ]' in guide
    assert 'CURRENT_CONTEXT="$(kubectl config current-context)"' in guide


def test_course_overlays_do_not_render_mlflow() -> None:
    for name in ("baseline", "candidate-b", "rollback"):
        rendered = overlay_documents(name)
        assert named_kind(rendered, "Ingress", "mlflow") is None
        assert named_kind(rendered, "Deployment", "mlflow") is None
        assert named_kind(rendered, "Service", "mlflow") is None
        assert named_kind(rendered, "PersistentVolumeClaim", "course-mlflow") is None
