"""Kubernetes, KServe, secret, and Alloy deployment contracts."""

import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path("deploy/k8s/base")
ALLOY = Path("deploy/k8s/alloy")
RUNTIME_IMAGE_EVIDENCE = Path(
    "docs/evidence/deployment/runtime-images-v2-20260908.json"
)
BASELINE_MODEL_SHA256 = (
    "f2576f12512a490c9814e5238c3f0d2a421a21637a4b03c882df6ff25a637edc"
)
ALLOY_IMAGE = (
    "grafana/alloy@sha256:"
    "51aeb9d829239345070619dad3edd6873186f913c84f45b365b74574fcb38ec0"
)


def documents(path: str, root: Path = ROOT) -> list[dict[str, object]]:
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


def risk_api_ingress(
    rendered: list[dict[str, object]],
) -> dict[str, object]:
    matches = [
        item
        for item in rendered
        if item.get("kind") == "Ingress"
        and item.get("metadata", {}).get("name") == "risk-api"
    ]
    assert matches, "expected risk-api Ingress in overlay render"
    return matches[0]


def runtime_image_evidence() -> dict[str, object]:
    """Load the recorded runtime image publication and verification facts."""
    return json.loads(RUNTIME_IMAGE_EVIDENCE.read_text(encoding="utf-8"))


def test_risk_api_uses_internal_kserve_and_read_only_secret_volume() -> None:
    deployment = documents("risk-api.yaml")[0]
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item for item in container["env"]}

    assert environment["AIQA_API_MODEL_BACKEND"]["value"] == "kserve"
    assert "mortality-risk-predictor" in environment["AIQA_API_KSERVE_URL"]["value"]
    assert container["image"] == runtime_image_evidence()["images"]["risk_api"][
        "reference"
    ]
    assert deployment["spec"]["template"]["spec"]["imagePullSecrets"] == [
        {"name": "ghcr-pull"}
    ]
    secret_mount = next(
        item
        for item in container["volumeMounts"]
        if item["name"] == "runtime-secrets"
    )
    assert secret_mount["readOnly"] is True
    assert secret_mount["mountPath"] == "/var/run/secrets/aiqa/risk-api"


def test_runtime_image_evidence_matches_pinned_deployment_images() -> None:
    evidence = runtime_image_evidence()
    images = evidence["images"]
    latest_build_input_commit = subprocess.run(
        (
            "git",
            "log",
            "-1",
            "--format=%H",
            "--",
            ".dockerignore",
            "pyproject.toml",
            "uv.lock",
            "apps",
            "packages",
        ),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    risk_api = documents("risk-api.yaml")[0]["spec"]["template"]["spec"][
        "containers"
    ][0]["image"]
    predictor = documents("inference-service.yaml")[0]["spec"]["predictor"][
        "containers"
    ][0]["image"]

    assert evidence["schema_version"] == 1
    assert len(evidence["source_commit"]) == 40
    assert evidence["source_commit"] == latest_build_input_commit
    assert evidence["local_verification"]["status"] == "verified"
    assert evidence["target_verification"]["status"] == "pending"
    assert evidence["target_verification"]["owner"] == "instructor_platform"
    assert evidence["target_verification"]["required_inputs"]
    assert evidence["target_verification"]["completion_evidence"]
    assert set(images) == {"risk_api", "kserve_predictor"}
    assert risk_api == images["risk_api"]["reference"]
    assert predictor == images["kserve_predictor"]["reference"]
    assert images["risk_api"]["platforms"] == ["linux/amd64", "linux/arm64"]
    assert images["kserve_predictor"]["platforms"] == [
        "linux/amd64",
        "linux/arm64",
    ]
    for image in images.values():
        assert set(image["platform_manifest_digests"]) == set(
            image["platforms"]
        )
        assert all(
            digest.startswith("sha256:") and len(digest) == 71
            for digest in image["platform_manifest_digests"].values()
        )
    source_tag = f":v2-{evidence['source_commit'][:12]}"
    assert images["risk_api"]["tag"].endswith(source_tag)
    assert images["kserve_predictor"]["tag"].endswith(source_tag)


def test_base_starts_with_baseline_model() -> None:
    service = documents("inference-service.yaml")[0]
    serialized = yaml.safe_dump(service)
    container = service["spec"]["predictor"]["containers"][0]
    environment = {item["name"]: item for item in container["env"]}

    assert service["kind"] == "InferenceService"
    assert service["metadata"]["annotations"]["serving.kserve.io/deploymentMode"] == (
        "RawDeployment"
    )
    assert "baseline-f2576f12512a" in serialized
    assert "candidate-a" not in serialized
    assert container["image"] == runtime_image_evidence()["images"][
        "kserve_predictor"
    ]["reference"]
    assert service["spec"]["predictor"]["imagePullSecrets"] == [{"name": "ghcr-pull"}]
    assert container["command"] == ["aiqa-kserve-predictor"]
    predictor_secrets = next(
        item
        for item in service["spec"]["predictor"]["volumes"]
        if item["name"] == "runtime-secrets"
    )
    assert predictor_secrets["projected"]["sources"][0]["secret"]["name"] == (
        "kserve-predictor-runtime"
    )
    assert environment["AIQA_KSERVE_TELEMETRY_CONFIG_PATH"]["value"] == (
        "/runtime/config/telemetry.yaml"
    )
    assert environment["AIQA_KSERVE_OTLP_ENDPOINT"]["value"] == (
        "http://alloy.tta-aiqa.svc.cluster.local:4318"
    )
    assert environment["AIQA_KSERVE_EXPECTED_MODEL_SHA256"]["valueFrom"] == {
        "configMapKeyRef": {
            "name": "model-identity",
            "key": "AIQA_KSERVE_EXPECTED_MODEL_SHA256",
        }
    }
    assert service["spec"]["predictor"]["labels"]["app.kubernetes.io/part-of"] == (
        "tta-aiqa"
    )


def test_kubernetes_deploys_alloy_but_no_monitoring_backend() -> None:
    manifests = "\n".join(
        path.read_text(encoding="utf-8") for path in ALLOY.glob("*.yaml")
    ).lower()
    alloy = documents("alloy.yaml", ALLOY)[0]
    container = alloy["spec"]["template"]["spec"]["containers"][0]

    assert ALLOY_IMAGE in manifests
    assert all(
        f"name: {name}\n" not in manifests
        for name in ("grafana", "loki", "tempo", "prometheus")
    )
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False


def test_alloy_collects_all_aiqa_workload_logs_and_otlp_traces() -> None:
    config = (ALLOY / "config.alloy").read_text(encoding="utf-8")

    assert 'discovery.relabel "aiqa_logs"' in config
    assert "__meta_kubernetes_pod_label_app_kubernetes_io_part_of" in config
    assert 'regex         = "tta-aiqa"' in config
    assert 'regex         = "alloy"' in config
    assert 'otelcol.receiver.otlp "aiqa"' in config
    assert 'otelcol.processor.batch "aiqa"' in config
    assert "username = string.trim_space(local.file.otlp_username.content)" in config
    assert "password = local.file.api_key.content" in config
    assert "client_auth" not in config


def test_shared_cluster_bounds_namespace_objects_and_alloy_ingress() -> None:
    quota = documents("resource-quota.yaml")[0]
    policy = documents("network-policy.yaml", ALLOY)[0]

    assert quota["kind"] == "ResourceQuota"
    assert quota["spec"]["hard"] == {
        "count/configmaps": "50",
        "count/persistentvolumeclaims": "10",
        "count/pods": "30",
        "count/secrets": "50",
        "count/services": "30",
    }
    assert policy["kind"] == "NetworkPolicy"
    assert policy["spec"]["podSelector"]["matchLabels"] == {
        "app.kubernetes.io/name": "alloy"
    }
    source = policy["spec"]["ingress"][0]["from"][0]["podSelector"]["matchLabels"]
    assert source == {"app.kubernetes.io/part-of": "tta-aiqa"}
    assert {item["port"] for item in policy["spec"]["ingress"][0]["ports"]} == {
        4318
    }

    alloy_service = next(
        document
        for document in documents("alloy.yaml", ALLOY)
        if document["kind"] == "Service"
    )
    assert {item["port"] for item in alloy_service["spec"]["ports"]} == {4318}


def test_candidate_and_rollback_overlays_select_only_approved_models() -> None:
    candidate = Path(
        "deploy/k8s/candidate-b/kustomization.yaml"
    ).read_text(encoding="utf-8")
    rollback = Path(
        "deploy/k8s/rollback/kustomization.yaml"
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
    model_identity = next(
        item
        for item in kustomization["configMapGenerator"]
        if item["name"] == "model-identity"
    )
    assert model_identity["envs"] == ["config/model-identity.env"]
    assert (
        (ROOT / "config/model-identity.env").read_text(encoding="utf-8").strip()
        == f"AIQA_KSERVE_EXPECTED_MODEL_SHA256={BASELINE_MODEL_SHA256}"
    )


def test_secret_creation_guides_fail_closed_on_kubernetes_context() -> None:
    guides = (
        Path("deploy/k8s/README.md"),
        Path("deploy/secrets/alloy/README.md"),
    )

    for path in guides:
        guide = path.read_text(encoding="utf-8")
        assert 'if [ -z "${TARGET_CONTEXT:-}" ]' in guide
        assert 'CURRENT_CONTEXT="$(kubectl config current-context)"' in guide
        assert 'if [ "$CURRENT_CONTEXT" != "$TARGET_CONTEXT" ]' in guide
        assert 'kubectl --context "$TARGET_CONTEXT" -n tta-aiqa' in guide


def test_risk_api_ingress_routes_clusterip_without_hostname() -> None:
    ingress = documents("risk-api-ingress.yaml")[0]
    rule = ingress["spec"]["rules"][0]
    path = rule["http"]["paths"][0]
    backend = path["backend"]["service"]

    assert ingress["kind"] == "Ingress"
    assert ingress["metadata"]["name"] == "risk-api"
    assert ingress["metadata"]["namespace"] == "tta-aiqa"
    assert ingress["metadata"]["labels"]["app.kubernetes.io/name"] == "risk-api"
    assert ingress["spec"]["ingressClassName"] == "traefik"
    assert "host" not in rule
    assert path["path"] == "/"
    assert path["pathType"] == "Prefix"
    assert backend["name"] == "risk-api"
    assert backend["port"]["name"] == "http"
    assert "tls" not in ingress["spec"]


def test_baseline_overlay_renders_risk_api_ingress_without_hostname() -> None:
    ingress = risk_api_ingress(overlay_documents("baseline"))
    rule = ingress["spec"]["rules"][0]
    backend = rule["http"]["paths"][0]["backend"]["service"]

    assert ingress["spec"]["ingressClassName"] == "traefik"
    assert "host" not in rule
    assert backend["name"] == "risk-api"
    assert backend["port"]["name"] == "http"


def test_candidate_and_rollback_overlays_inherit_risk_api_ingress() -> None:
    for name in ("candidate-b", "rollback"):
        ingress = risk_api_ingress(overlay_documents(name))
        rule = ingress["spec"]["rules"][0]
        backend = rule["http"]["paths"][0]["backend"]["service"]

        assert ingress["metadata"]["namespace"] == "tta-aiqa"
        assert ingress["spec"]["ingressClassName"] == "traefik"
        assert "host" not in rule
        assert backend["name"] == "risk-api"
        assert backend["port"]["name"] == "http"
