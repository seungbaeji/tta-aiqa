"""Tests for read-only target release verification."""

from __future__ import annotations

import json
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
verifier = import_module("scripts.verify_target_release")

RISK_INDEX = "sha256:" + "1" * 64
RISK_PLATFORM = "sha256:" + "2" * 64
PREDICTOR_INDEX = "sha256:" + "3" * 64
PREDICTOR_PLATFORM = "sha256:" + "4" * 64
RISK_REFERENCE = f"ghcr.io/example/risk-api@{RISK_INDEX}"
PREDICTOR_REFERENCE = f"ghcr.io/example/predictor@{PREDICTOR_INDEX}"


def image_evidence() -> dict[str, Any]:
    return {
        "images": {
            "risk_api": {
                "reference": RISK_REFERENCE,
                "platform_manifest_digests": {
                    "linux/amd64": RISK_PLATFORM,
                },
            },
            "kserve_predictor": {
                "reference": PREDICTOR_REFERENCE,
                "platform_manifest_digests": {
                    "linux/amd64": PREDICTOR_PLATFORM,
                },
            },
        }
    }


def pod(
    *,
    name: str,
    container_name: str,
    image: str,
    image_digest: str,
) -> dict[str, Any]:
    return {
        "metadata": {"name": name},
        "spec": {
            "containers": [
                {
                    "name": container_name,
                    "image": image,
                }
            ]
        },
        "status": {
            "phase": "Running",
            "containerStatuses": [
                {
                    "name": container_name,
                    "ready": True,
                    "imageID": f"{image.split('@', 1)[0]}@{image_digest}",
                }
            ],
        },
    }


def snapshot(release: str = "candidate-b") -> dict[str, Any]:
    expectation = verifier.RELEASES[release]
    annotations = {"aiqa.tta/model-release": expectation.version}
    if expectation.release_action:
        annotations["aiqa.tta/release-action"] = expectation.release_action
    return {
        "namespace": {"metadata": {"name": "tta-aiqa"}},
        "registry_secret": {
            "metadata": {"name": "ghcr-pull"},
            "type": "kubernetes.io/dockerconfigjson",
        },
        "model_pvc": {
            "metadata": {"name": "course-models"},
            "status": {"phase": "Bound"},
        },
        "model_identity": {
            "data": {
                "AIQA_KSERVE_EXPECTED_MODEL_SHA256": expectation.model_sha256,
            }
        },
        "risk_deployment": {
            "metadata": {"generation": 4, "annotations": annotations},
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "risk-api",
                                "image": RISK_REFERENCE,
                                "volumeMounts": [
                                    {"name": "config"},
                                    {
                                        "name": "model",
                                        "subPath": expectation.model_subpath,
                                    },
                                ],
                            }
                        ]
                    }
                },
            },
            "status": {
                "observedGeneration": 4,
                "availableReplicas": 1,
                "updatedReplicas": 1,
            },
        },
        "inference_service": {
            "metadata": {"generation": 7, "annotations": annotations},
            "spec": {
                "predictor": {
                    "containers": [
                        {
                            "name": "kserve-container",
                            "image": PREDICTOR_REFERENCE,
                            "volumeMounts": [
                                {
                                    "name": "model",
                                    "subPath": expectation.model_subpath,
                                }
                            ],
                        }
                    ]
                }
            },
            "status": {
                "observedGeneration": 7,
                "conditions": [{"type": "Ready", "status": "True"}],
            },
        },
        "risk_pods": {
            "items": [
                pod(
                    name="risk-api-abc",
                    container_name="risk-api",
                    image=RISK_REFERENCE,
                    image_digest=RISK_PLATFORM,
                )
            ]
        },
        "predictor_pods": {
            "items": [
                pod(
                    name="mortality-risk-predictor-abc",
                    container_name="kserve-container",
                    image=PREDICTOR_REFERENCE,
                    image_digest=PREDICTOR_PLATFORM,
                )
            ]
        },
    }


def test_release_expectations_keep_candidate_and_rollback_distinct() -> None:
    baseline = verifier.RELEASES["baseline"]
    candidate = verifier.RELEASES["candidate-b"]
    rollback = verifier.RELEASES["rollback"]

    assert baseline.profile == rollback.profile == "baseline"
    assert baseline.version == rollback.version == "baseline-f2576f12512a"
    assert candidate.profile == "candidate-b"
    assert candidate.version == "candidate-b-c712a8e52344"
    assert candidate.model_sha256 != baseline.model_sha256
    assert rollback.release_action == "rollback"


def test_kubernetes_state_accepts_exact_release_and_platform_digests() -> None:
    checks = verifier.verify_kubernetes_state(
        snapshot(),
        verifier.RELEASES["candidate-b"],
        image_evidence(),
    )

    assert checks
    assert all(check.status == "pass" for check in checks)
    details = " ".join(check.detail for check in checks)
    assert RISK_PLATFORM in details
    assert PREDICTOR_PLATFORM in details


def test_kubernetes_state_rejects_stale_model_and_unready_runtime() -> None:
    state = snapshot()
    state["model_identity"]["data"][
        "AIQA_KSERVE_EXPECTED_MODEL_SHA256"
    ] = "wrong"
    state["predictor_pods"]["items"][0]["status"]["containerStatuses"][0][
        "ready"
    ] = False

    checks = verifier.verify_kubernetes_state(
        state,
        verifier.RELEASES["candidate-b"],
        image_evidence(),
    )

    failures = {check.name for check in checks if check.status == "fail"}
    assert "model_identity" in failures
    assert "predictor_runtime" in failures


def test_context_mismatch_fails_before_cluster_resource_queries(
    monkeypatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(
            args=arguments,
            returncode=0,
            stdout="wrong-context\n",
            stderr="",
        )

    monkeypatch.setattr(verifier, "_command", command)

    context = verifier.check_context("approved-course")

    assert context.status == "fail"
    assert calls == [("kubectl", "config", "current-context")]


def test_api_state_checks_identity_and_valid_prediction_without_payload_leak() -> None:
    expectation = verifier.RELEASES["candidate-b"]
    private_feature = 987654.321
    calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def request_json(
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        calls.append((method, url, payload))
        if url.endswith("/health/ready"):
            return 200, {"status": "ready", "model_version": expectation.version}, {}
        if url.endswith("/v1/model"):
            return (
                200,
                {
                    "backend": "kserve",
                    "profile": expectation.profile,
                    "version": expectation.version,
                    "threshold": expectation.threshold,
                    "feature_count": 133,
                    "education_only": True,
                },
                {},
            )
        request_id = headers["X-Request-ID"]
        return (
            200,
            {
                "request_id": request_id,
                "model_profile": expectation.profile,
                "model_version": expectation.version,
                "education_only": True,
            },
            {"x-request-id": request_id},
        )

    checks = verifier.verify_api_state(
        "https://risk.example.test/course",
        expectation,
        {"features": {"age": private_feature}},
        request_json=request_json,
    )

    assert all(check.status == "pass" for check in checks)
    assert [call[0] for call in calls] == ["GET", "GET", "POST"]
    assert str(private_feature) not in json.dumps(
        [check.detail for check in checks]
    )
    prediction = next(
        check for check in checks if check.name == "target_prediction"
    )
    assert prediction.evidence is not None
    assert prediction.evidence["request_id"].startswith("target-")
    assert prediction.evidence["run_id"].startswith("target-")
    assert prediction.evidence["model_version"] == expectation.version


def test_report_does_not_claim_live_telemetry_verification() -> None:
    result = verifier.report(
        release="candidate-b",
        context="approved-course",
        checks=[verifier.Check("release", "pass", "verified")],
    )

    assert result["release_passed"] is True
    assert result["live_telemetry_status"] == "not_checked"
    assert "target_verified" not in json.dumps(result)
