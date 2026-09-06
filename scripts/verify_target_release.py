"""Verify one synchronized course release without changing the target cluster."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "tta-aiqa"
DEFAULT_EVIDENCE = (
    ROOT / "docs/reference/evidence/deployment/runtime-images-v2.json"
)
DEFAULT_CONTRACT = ROOT / "configs/contracts/model-input.yaml"
DEFAULT_SAMPLE = (
    ROOT
    / "data/splits/physionet-2012/revisions/v2/datasets/operational.csv"
)
DEFAULT_OUTPUT = ROOT / "artifacts/reports/target-release-verification.json"


@dataclass(frozen=True)
class Check:
    """One bounded verification result that contains no secret or feature values."""

    name: str
    status: str
    detail: str
    required: bool = True
    evidence: dict[str, Any] | None = None


@dataclass(frozen=True)
class ReleaseExpectation:
    """Expected identity and model path for one approved release stage."""

    profile: str
    version: str
    threshold: float
    model_sha256: str
    model_subpath: str
    release_action: str | None = None


BASELINE_SHA256 = (
    "f2576f12512a490c9814e5238c3f0d2a421a21637a4b03c882df6ff25a637edc"
)
CANDIDATE_B_SHA256 = (
    "c712a8e52344c09a493629f8e6a0283c6c3139fb46cc53e293a44ee490a07c95"
)
RELEASES = {
    "baseline": ReleaseExpectation(
        profile="baseline",
        version="baseline-f2576f12512a",
        threshold=0.50,
        model_sha256=BASELINE_SHA256,
        model_subpath="physionet-2012/v2/baseline-f2576f12512a",
    ),
    "candidate-b": ReleaseExpectation(
        profile="candidate-b",
        version="candidate-b-c712a8e52344",
        threshold=0.35,
        model_sha256=CANDIDATE_B_SHA256,
        model_subpath="physionet-2012/v2/candidate-b-c712a8e52344",
    ),
    "rollback": ReleaseExpectation(
        profile="baseline",
        version="baseline-f2576f12512a",
        threshold=0.50,
        model_sha256=BASELINE_SHA256,
        model_subpath="physionet-2012/v2/baseline-f2576f12512a",
        release_action="rollback",
    ),
}


def _command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def check_context(expected_context: str | None) -> Check:
    """Fail before any cluster query unless the exact approved context is active."""
    if not expected_context:
        return Check(
            "kubernetes_context",
            "fail",
            "--expected-context must name the approved course context",
        )
    try:
        result = _command(("kubectl", "config", "current-context"))
    except OSError:
        return Check(
            "kubernetes_context",
            "fail",
            "kubectl is unavailable; no cluster resources were queried",
        )
    current = result.stdout.strip()
    if result.returncode != 0 or current != expected_context:
        return Check(
            "kubernetes_context",
            "fail",
            f"expected {expected_context!r}; current context does not match",
        )
    return Check(
        "kubernetes_context",
        "pass",
        f"matched approved context {expected_context!r}",
    )


def _kubectl_json(
    context: str,
    resource: str,
    *,
    name: str | None = None,
    label: str | None = None,
    namespaced: bool = True,
) -> dict[str, Any]:
    arguments = ["kubectl", "--context", context]
    if namespaced:
        arguments.extend(("-n", NAMESPACE))
    arguments.extend(("get", resource))
    if name:
        arguments.append(name)
    if label:
        arguments.extend(("-l", label))
    arguments.extend(("-o", "json"))
    result = _command(tuple(arguments))
    if result.returncode != 0:
        raise RuntimeError(f"unable to read required {resource}")
    document = json.loads(result.stdout)
    if not isinstance(document, dict):
        raise RuntimeError(f"invalid JSON returned for {resource}")
    return document


def collect_kubernetes_snapshot(context: str) -> dict[str, Any]:
    """Read only the bounded resources needed to verify the release."""
    return {
        "namespace": _kubectl_json(
            context,
            "namespace",
            name=NAMESPACE,
            namespaced=False,
        ),
        "registry_secret": _kubectl_json(
            context,
            "secret",
            name="ghcr-pull",
        ),
        "model_pvc": _kubectl_json(
            context,
            "pvc",
            name="course-models",
        ),
        "model_identity": _kubectl_json(
            context,
            "configmap",
            name="model-identity",
        ),
        "risk_deployment": _kubectl_json(
            context,
            "deployment",
            name="risk-api",
        ),
        "inference_service": _kubectl_json(
            context,
            "inferenceservice",
            name="mortality-risk",
        ),
        "risk_pods": _kubectl_json(
            context,
            "pods",
            label="app.kubernetes.io/name=risk-api",
        ),
        "predictor_pods": _kubectl_json(
            context,
            "pods",
            label="app.kubernetes.io/name=kserve-risk-predictor",
        ),
    }


def _container(
    containers: list[dict[str, Any]],
    name: str,
) -> dict[str, Any] | None:
    return next(
        (container for container in containers if container.get("name") == name),
        None,
    )


def _model_subpath(container: dict[str, Any] | None) -> str | None:
    if container is None:
        return None
    mount = next(
        (
            item
            for item in container.get("volumeMounts", [])
            if item.get("name") == "model"
        ),
        None,
    )
    return mount.get("subPath") if mount else None


def _annotation_check(
    state: dict[str, Any],
    expectation: ReleaseExpectation,
) -> Check:
    expected = {"aiqa.tta/model-release": expectation.version}
    if expectation.release_action:
        expected["aiqa.tta/release-action"] = expectation.release_action
    annotations = [
        resource.get("metadata", {}).get("annotations", {})
        for resource in (
            state["risk_deployment"],
            state["inference_service"],
        )
    ]
    matched = all(
        all(annotation.get(key) == value for key, value in expected.items())
        for annotation in annotations
    )
    unexpected_action = (
        expectation.release_action is None
        and any(
            "aiqa.tta/release-action" in annotation
            for annotation in annotations
        )
    )
    if not matched or unexpected_action:
        return Check(
            "release_annotation",
            "fail",
            "workload annotations do not match the selected release stage",
        )
    return Check(
        "release_annotation",
        "pass",
        f"workload annotations select {expectation.version}",
    )


def _runtime_check(
    *,
    name: str,
    pods: dict[str, Any],
    container_name: str,
    image_reference: str,
    accepted_digests: set[str],
) -> Check:
    items = pods.get("items", [])
    if not items:
        return Check(name, "fail", "no matching runtime Pod was found")

    observed: set[str] = set()
    for pod in items:
        spec_container = _container(
            pod.get("spec", {}).get("containers", []),
            container_name,
        )
        status_container = _container(
            pod.get("status", {}).get("containerStatuses", []),
            container_name,
        )
        image_id = (status_container or {}).get("imageID", "")
        digest = image_id.rsplit("@", 1)[-1] if "@" in image_id else ""
        if (
            pod.get("status", {}).get("phase") != "Running"
            or spec_container is None
            or spec_container.get("image") != image_reference
            or status_container is None
            or status_container.get("ready") is not True
            or digest not in accepted_digests
        ):
            return Check(
                name,
                "fail",
                "a runtime Pod is unready or does not use an accepted "
                "platform manifest digest",
            )
        observed.add(digest)
    return Check(
        name,
        "pass",
        "ready runtime Pod digest(s): " + ", ".join(sorted(observed)),
    )


def verify_kubernetes_state(
    state: dict[str, Any],
    expectation: ReleaseExpectation,
    image_evidence: dict[str, Any],
) -> list[Check]:
    """Verify desired and running state from a read-only Kubernetes snapshot."""
    images = image_evidence["images"]
    risk_reference = images["risk_api"]["reference"]
    predictor_reference = images["kserve_predictor"]["reference"]
    risk_digests = set(
        images["risk_api"]["platform_manifest_digests"].values()
    )
    predictor_digests = set(
        images["kserve_predictor"]["platform_manifest_digests"].values()
    )

    namespace_ok = (
        state["namespace"].get("metadata", {}).get("name") == NAMESPACE
    )
    secret_ok = (
        state["registry_secret"].get("metadata", {}).get("name")
        == "ghcr-pull"
        and state["registry_secret"].get("type")
        == "kubernetes.io/dockerconfigjson"
    )
    pvc_ok = state["model_pvc"].get("status", {}).get("phase") == "Bound"

    risk = state["risk_deployment"]
    risk_spec = risk.get("spec", {})
    risk_status = risk.get("status", {})
    risk_container = _container(
        risk_spec.get("template", {}).get("spec", {}).get("containers", []),
        "risk-api",
    )
    desired_replicas = risk_spec.get("replicas", 1)
    risk_ready = (
        risk_status.get("observedGeneration")
        == risk.get("metadata", {}).get("generation")
        and risk_status.get("availableReplicas", 0) >= desired_replicas
        and risk_status.get("updatedReplicas", 0) >= desired_replicas
    )
    risk_desired = (
        risk_container is not None
        and risk_container.get("image") == risk_reference
        and _model_subpath(risk_container) == expectation.model_subpath
    )

    service = state["inference_service"]
    service_status = service.get("status", {})
    predictor = _container(
        service.get("spec", {})
        .get("predictor", {})
        .get("containers", []),
        "kserve-container",
    )
    observed_generation = service_status.get("observedGeneration")
    service_generation_ok = (
        observed_generation is None
        or observed_generation == service.get("metadata", {}).get("generation")
    )
    service_ready = (
        service_generation_ok
        and any(
            condition.get("type") == "Ready"
            and condition.get("status") == "True"
            for condition in service_status.get("conditions", [])
        )
    )
    predictor_desired = (
        predictor is not None
        and predictor.get("image") == predictor_reference
        and _model_subpath(predictor) == expectation.model_subpath
    )
    identity_ok = (
        state["model_identity"].get("data", {}).get(
            "AIQA_KSERVE_EXPECTED_MODEL_SHA256"
        )
        == expectation.model_sha256
    )

    checks = [
        Check(
            "namespace",
            "pass" if namespace_ok else "fail",
            "course namespace exists"
            if namespace_ok
            else "course namespace is missing or mismatched",
        ),
        Check(
            "registry_secret",
            "pass" if secret_ok else "fail",
            "ghcr-pull has the expected Secret type"
            if secret_ok
            else "ghcr-pull is missing or has the wrong Secret type",
        ),
        Check(
            "model_pvc",
            "pass" if pvc_ok else "fail",
            "course-models PVC is Bound"
            if pvc_ok
            else "course-models PVC is not Bound",
        ),
        _annotation_check(state, expectation),
        Check(
            "model_identity",
            "pass" if identity_ok else "fail",
            f"model identity matches {expectation.model_sha256}"
            if identity_ok
            else "model identity does not match the selected release",
        ),
        Check(
            "risk_api_desired_state",
            "pass" if risk_desired and risk_ready else "fail",
            "Risk API image, model path, and rollout are current"
            if risk_desired and risk_ready
            else "Risk API desired state or rollout is stale",
        ),
        Check(
            "predictor_desired_state",
            "pass" if predictor_desired and service_ready else "fail",
            "predictor image, model path, and readiness are current"
            if predictor_desired and service_ready
            else "predictor desired state or readiness is stale",
        ),
        _runtime_check(
            name="risk_api_runtime",
            pods=state["risk_pods"],
            container_name="risk-api",
            image_reference=risk_reference,
            accepted_digests=risk_digests,
        ),
        _runtime_check(
            name="predictor_runtime",
            pods=state["predictor_pods"],
            container_name="kserve-container",
            image_reference=predictor_reference,
            accepted_digests=predictor_digests,
        ),
    ]
    return checks


def _http_url_is_valid(value: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return False
    path = parsed.path.rstrip("/")
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
        and not path.endswith(("/health/ready", "/v1/model", "/v1/predict"))
    )


def _request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    headers: dict[str, str],
) -> tuple[int, dict[str, Any], dict[str, str]]:
    data = (
        json.dumps(payload, separators=(",", ":")).encode()
        if payload is not None
        else None
    )
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        document = json.loads(response.read())
        response_headers = {
            key.lower(): value for key, value in response.headers.items()
        }
        return response.status, document, response_headers


def verify_api_state(
    target_url: str,
    expectation: ReleaseExpectation,
    payload: dict[str, Any],
    *,
    request_json: Callable[
        [str, str, dict[str, Any] | None, dict[str, str]],
        tuple[int, dict[str, Any], dict[str, str]],
    ] = _request_json,
) -> list[Check]:
    """Verify model identity and one valid request without reporting features."""
    if not _http_url_is_valid(target_url):
        return [
            Check(
                "target_url",
                "fail",
                "--target-url must be an HTTP(S) API base URL without "
                "credentials, query, or fragment",
            )
        ]
    base = target_url.rstrip("/")
    request_id = f"target-{uuid.uuid4()}"
    run_id = f"target-{uuid.uuid4()}"
    headers = {
        "X-Request-ID": request_id,
        "X-AIQA-Run-ID": run_id,
        "X-AIQA-Scenario": "baseline",
    }
    started_at = _utc_now()
    try:
        ready_status, ready, _ = request_json(
            "GET",
            base + "/health/ready",
            None,
            {},
        )
        model_status, model, _ = request_json(
            "GET",
            base + "/v1/model",
            None,
            {},
        )
        predict_status, prediction, response_headers = request_json(
            "POST",
            base + "/v1/predict",
            payload,
            headers,
        )
        completed_at = _utc_now()
    except (
        OSError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ):
        return [
            Check(
                "target_api",
                "fail",
                "target API request failed or returned invalid JSON",
            )
        ]

    ready_ok = (
        ready_status == 200
        and ready.get("status") == "ready"
        and ready.get("model_version") == expectation.version
    )
    model_ok = (
        model_status == 200
        and model.get("backend") == "kserve"
        and model.get("profile") == expectation.profile
        and model.get("version") == expectation.version
        and model.get("threshold") == expectation.threshold
        and model.get("feature_count") == 133
        and model.get("education_only") is True
    )
    prediction_ok = (
        predict_status == 200
        and prediction.get("request_id") == request_id
        and response_headers.get("x-request-id") == request_id
        and prediction.get("model_profile") == expectation.profile
        and prediction.get("model_version") == expectation.version
        and prediction.get("education_only") is True
    )
    return [
        Check(
            "target_readiness",
            "pass" if ready_ok else "fail",
            f"readiness exposes {expectation.version}"
            if ready_ok
            else "readiness does not match the selected release",
        ),
        Check(
            "target_model_identity",
            "pass" if model_ok else "fail",
            f"model endpoint exposes {expectation.profile}/{expectation.version}"
            if model_ok
            else "model endpoint identity or contract is mismatched",
        ),
        Check(
            "target_prediction",
            "pass" if prediction_ok else "fail",
            "valid request returned HTTP 200 with request ID "
            f"{request_id} and run ID {run_id}"
            if prediction_ok
            else "valid request did not preserve the selected model identity",
            evidence={
                "started_at": started_at,
                "completed_at": completed_at,
                "request_id": request_id,
                "run_id": run_id,
                "model_profile": expectation.profile,
                "model_version": expectation.version,
            }
            if prediction_ok
            else None,
        ),
    ]


def load_sample_payload(
    contract_path: Path = DEFAULT_CONTRACT,
    sample_path: Path = DEFAULT_SAMPLE,
) -> dict[str, Any]:
    """Load one bounded local sample without copying values into the report."""
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    with sample_path.open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))

    features: dict[str, Any] = {}
    for specification in contract["features"]:
        name = specification["name"]
        raw = row[name]
        if raw == "":
            value: Any = None
        elif specification["dtype"] == "boolean":
            numeric = float(raw)
            if numeric not in {0.0, 1.0}:
                raise ValueError(f"{name} is not a boolean marker")
            value = bool(numeric)
        else:
            value = float(raw)
        features[name] = value
    return {"features": features}


def report(
    *,
    release: str,
    context: str,
    checks: list[Check],
) -> dict[str, Any]:
    """Build an honest stage report without claiming live telemetry."""
    return {
        "schema_version": 1,
        "scope": "kubernetes-release",
        "release": release,
        "context": context,
        "namespace": NAMESPACE,
        "checked_at": _utc_now(),
        "release_passed": not any(
            check.required and check.status != "pass" for check in checks
        ),
        "live_telemetry_status": "not_checked",
        "checks": [asdict(check) for check in checks],
    }


def _utc_now() -> str:
    return (
        datetime.now(tz=UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _write_report(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-context",
        required=True,
        help="exact course context approved by the cluster operator",
    )
    parser.add_argument(
        "--release",
        choices=tuple(RELEASES),
        required=True,
        help="release stage already synchronized by the platform workflow",
    )
    parser.add_argument(
        "--target-url",
        required=True,
        help="Risk API HTTP(S) base URL",
    )
    parser.add_argument(
        "--runtime-image-evidence",
        type=Path,
        default=DEFAULT_EVIDENCE,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    checks = [check_context(args.expected_context)]
    if checks[0].status == "pass":
        try:
            image_evidence = json.loads(
                args.runtime_image_evidence.read_text(encoding="utf-8")
            )
            state = collect_kubernetes_snapshot(args.expected_context)
            cluster_checks = verify_kubernetes_state(
                state,
                RELEASES[args.release],
                image_evidence,
            )
            checks.extend(cluster_checks)
            if all(check.status == "pass" for check in cluster_checks):
                checks.extend(
                    verify_api_state(
                        args.target_url,
                        RELEASES[args.release],
                        load_sample_payload(),
                    )
                )
        except (KeyError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
            checks.append(
                Check(
                    "target_snapshot",
                    "fail",
                    "required target state or local verification input "
                    "could not be read",
                )
            )

    document = report(
        release=args.release,
        context=args.expected_context,
        checks=checks,
    )
    _write_report(args.output, document)
    for check in checks:
        print(f"[{check.status.upper():4}] {check.name}: {check.detail}")
    print(f"wrote release verification: {args.output}")
    print("live telemetry remains not_checked and must be verified separately")
    return 0 if document["release_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
