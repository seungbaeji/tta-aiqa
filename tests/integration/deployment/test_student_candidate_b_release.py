"""Student Candidate B release: patch an existing Argo app, never kubectl-create one."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.platform.publish_model import assert_candidate_b_is_released
from scripts.platform.sync_student_release import (
    CANDIDATE_B_PATH,
    CANDIDATE_B_VERSION,
    SyncBlocked,
    sync_existing_release,
)

STUDENT_COMMAND_FILES = (
    Path("labs/chapters/ch03/README.md"),
    Path("labs/chapters/ch05/README.md"),
    Path("labs/chapters/ch03/02_release_candidate_b.ipynb"),
    Path("scripts/platform/sync_student_release.py"),
)
FORBIDDEN_CREATE_COMMANDS = (
    "argocd app create",
    "kubectl create",
    "kubectl apply",
    "render_argocd_application.py",
)
OVERLAY = Path("deploy/k8s/candidate-b/kustomization.yaml")
SCRIPT = Path("scripts/platform/sync_student_release.py")
PUBLISH = Path("scripts/platform/publish_model.py")
CH03 = Path("labs/chapters/ch03/README.md")
CH05 = Path("labs/chapters/ch05/README.md")
ARGOCD = Path("deploy/argocd/README.md")
ROOT_README = Path("README.md")


def _combined(paths: tuple[Path, ...]) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def application_document(
    *,
    destination_server: str = "https://student.example.test:6443",
    path: str = "deploy/k8s/baseline",
    sync_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    destination: dict[str, str] = {"namespace": "tta-aiqa"}
    if destination_server:
        destination["server"] = destination_server
    return {
        "kind": "Application",
        "metadata": {"name": "tta-aiqa-student-201", "namespace": "argocd"},
        "spec": {
            "source": {
                "repoURL": "https://github.com/seungbaeji/tta-aiqa.git",
                "path": path,
                "targetRevision": "a" * 40,
            },
            "destination": destination,
            "syncPolicy": sync_policy or {"syncOptions": ["CreateNamespace=true"]},
        },
    }


def test_student_docs_and_script_do_not_include_application_create() -> None:
    combined = _combined(STUDENT_COMMAND_FILES)

    for command in FORBIDDEN_CREATE_COMMANDS:
        assert command not in combined
    assert "tta" in CH03.read_text(encoding="utf-8")
    assert "gitops.lab.mrml.dev" in CH03.read_text(encoding="utf-8")
    assert "Application 생성" in CH03.read_text(encoding="utf-8")
    assert "KServe 설치" in CH03.read_text(encoding="utf-8")


def test_student_sync_script_guards_target_context_before_cluster_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(
            args=arguments,
            returncode=0,
            stdout="student-201\n",
            stderr="",
        )

    monkeypatch.setattr("scripts.platform.sync_student_release._command", command)

    with pytest.raises(SyncBlocked, match="TARGET_CONTEXT is required"):
        sync_existing_release(
            application_name="tta-aiqa-student-201",
            target_context="",
        )
    with pytest.raises(SyncBlocked, match="TARGET_CONTEXT is required"):
        sync_existing_release(
            application_name="tta-aiqa-student-201",
            target_context=None,
        )

    assert calls == []

    script = SCRIPT.read_text(encoding="utf-8")
    assert "TARGET_CONTEXT" in script
    assert "current-context" in script
    assert "refusing to change a cluster" in script
    assert "kubectl apply" not in script
    assert "kubectl create" not in script
    assert "argocd app create" not in script


def test_student_sync_refuses_context_mismatch_before_get_or_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(
            args=arguments,
            returncode=0,
            stdout="other-context\n",
            stderr="",
        )

    monkeypatch.setattr("scripts.platform.sync_student_release._command", command)

    with pytest.raises(SyncBlocked, match="Context mismatch"):
        sync_existing_release(
            application_name="tta-aiqa-student-201",
            target_context="student-201",
        )

    assert calls == [("kubectl", "config", "current-context")]


def test_student_sync_does_not_create_a_missing_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        if arguments[:3] == ("kubectl", "config", "current-context"):
            return subprocess.CompletedProcess(
                args=arguments, returncode=0, stdout="student-201\n", stderr=""
            )
        return subprocess.CompletedProcess(
            args=arguments,
            returncode=1,
            stdout="",
            stderr=(
                "Error from server (NotFound): applications.argoproj.io "
                '"tta-aiqa-student-201" not found'
            ),
        )

    monkeypatch.setattr("scripts.platform.sync_student_release._command", command)

    with pytest.raises(SyncBlocked, match="refusing to create"):
        sync_existing_release(
            application_name="tta-aiqa-student-201",
            target_context="student-201",
        )

    assert all("patch" not in arguments for arguments in calls)
    assert all("apply" not in arguments for arguments in calls)
    assert all("create" not in arguments[1:] for arguments in calls)


def test_student_sync_refuses_in_cluster_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        if arguments[:3] == ("kubectl", "config", "current-context"):
            return subprocess.CompletedProcess(
                args=arguments, returncode=0, stdout="student-201\n", stderr=""
            )
        if "get" in arguments:
            return subprocess.CompletedProcess(
                args=arguments,
                returncode=0,
                stdout=json.dumps(
                    application_document(
                        destination_server="https://kubernetes.default.svc"
                    )
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {arguments}")

    monkeypatch.setattr("scripts.platform.sync_student_release._command", command)

    with pytest.raises(SyncBlocked, match="kubernetes.default.svc"):
        sync_existing_release(
            application_name="tta-aiqa-student-201",
            target_context="student-201",
        )


def test_student_sync_refuses_automated_prune_or_self_heal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        if arguments[:3] == ("kubectl", "config", "current-context"):
            return subprocess.CompletedProcess(
                args=arguments, returncode=0, stdout="student-201\n", stderr=""
            )
        if "get" in arguments:
            return subprocess.CompletedProcess(
                args=arguments,
                returncode=0,
                stdout=json.dumps(
                    application_document(
                        sync_policy={
                            "automated": {"prune": True, "selfHeal": True},
                            "syncOptions": ["CreateNamespace=true"],
                        }
                    )
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {arguments}")

    monkeypatch.setattr("scripts.platform.sync_student_release._command", command)

    with pytest.raises(SyncBlocked, match="automated prune/selfHeal"):
        sync_existing_release(
            application_name="tta-aiqa-student-201",
            target_context="student-201",
        )


def test_student_sync_patches_existing_app_to_candidate_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patches: list[str] = []

    def command(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        if arguments[:3] == ("kubectl", "config", "current-context"):
            return subprocess.CompletedProcess(
                args=arguments, returncode=0, stdout="student-201\n", stderr=""
            )
        if "get" in arguments:
            return subprocess.CompletedProcess(
                args=arguments,
                returncode=0,
                stdout=json.dumps(application_document()),
                stderr="",
            )
        if "patch" in arguments:
            payload = arguments[arguments.index("-p") + 1]
            patches.append(payload)
            return subprocess.CompletedProcess(
                args=arguments, returncode=0, stdout="patched\n", stderr=""
            )
        raise AssertionError(f"unexpected command: {arguments}")

    monkeypatch.setattr("scripts.platform.sync_student_release._command", command)

    result = sync_existing_release(
        application_name="tta-aiqa-student-201",
        target_context="student-201",
    )

    assert result["result"] == "synced"
    assert result["path"] == CANDIDATE_B_PATH
    assert result["expected_version"] == CANDIDATE_B_VERSION
    assert CANDIDATE_B_VERSION == "candidate-b-c712a8e52344"
    assert len(patches) == 1
    payload = json.loads(patches[0])
    assert payload["spec"]["source"]["path"] == CANDIDATE_B_PATH
    serialized = json.dumps(payload)
    assert "automated" not in serialized
    assert "selfHeal" not in serialized
    assert "prune" not in serialized
    assert "create" not in serialized


def test_candidate_b_overlay_keeps_approved_digest_and_excludes_candidate_a() -> None:
    overlay = OVERLAY.read_text(encoding="utf-8")

    assert "candidate-b-c712a8e52344" in overlay
    assert "c712a8e52344c09a493629f8e6a0283c6c3139fb46cc53e293a44ee490a07c95" in overlay
    assert "candidate-a" not in overlay
    assert "physionet-2012/v2/candidate-b-c712a8e52344" in overlay


def test_publish_model_still_requires_release_approved_candidate_b() -> None:
    source = PUBLISH.read_text(encoding="utf-8")

    assert 'release.get("release_status") != "release_approved"' in source
    assert "assert_candidate_b_is_released" in source
    with pytest.raises(PermissionError, match="not approved"):
        assert_candidate_b_is_released(
            {
                "release_status": "scenario_review",
                "deployment_allowed": True,
                "approved_profile": "candidate-b",
                "approved_model": {"profile": "candidate-b"},
            }
        )


def test_ch03_documents_student_publish_sync_and_target_model_get() -> None:
    guide = CH03.read_text(encoding="utf-8")

    assert (
        "scripts/platform/publish_model.py candidate-b --revision v2 "
        "--target-root /mnt/course-models"
    ) in guide
    assert "scripts/platform/sync_student_release.py" in guide
    assert "AIQA_RISK_API_URL" in guide
    assert "/v1/model" in guide
    assert "candidate-b-c712a8e52344" in guide
    assert "02_release_candidate_b.ipynb" in guide
    assert "result=BLOCKED" in guide
    assert "operational_deployment_scope=target_pending" in guide
    assert "http://127.0.0.1:8000" in guide
    assert "sealed test를 다시 평가한 것이 아니며" in guide
    assert "cluster 명령을 수행하지" not in guide
    assert "argocd app create" not in guide
    assert "render_argocd_application.py" not in guide


def test_student_docs_do_not_treat_compose_url_as_target_identity() -> None:
    ch03 = CH03.read_text(encoding="utf-8")
    serving = ROOT_README.read_text(encoding="utf-8")
    kubernetes = serving[serving.index("## 6. Serving과 Traffic") :]
    kubernetes = kubernetes[: kubernetes.index("## 8. 구현 검증")]

    assert "http://127.0.0.1:8000" in ch03
    assert "AIQA_RISK_API_URL" in ch03
    assert "섞지" in ch03
    assert "http://127.0.0.1:8000" in kubernetes
    assert "AIQA_RISK_API_URL" in kubernetes
    assert "scripts/platform/sync_student_release.py" in kubernetes
    assert "실제 동기화는 플랫폼 담당자가 수행합니다" not in kubernetes


def test_argocd_readme_documents_tta_ui_create_and_candidate_b_switch() -> None:
    guide = ARGOCD.read_text(encoding="utf-8")

    assert "TARGET_CONTEXT" in guide
    assert 'if [ -z "${TARGET_CONTEXT:-}" ]' in guide
    assert "scripts/platform/sync_student_release.py" in guide
    assert "scripts/platform/publish_model.py candidate-b" in guide
    assert "수강생은 공동 환경에서 이 파일을 적용하지 않습니다" not in guide
    assert "Application을 만들지 않습니다" not in guide
    assert "gitops.lab.mrml.dev" in guide
    assert "tta" in guide
    assert "kubectl apply" in guide
    assert "kubernetes.default.svc" in guide


def test_ch05_keeps_rollback_out_of_student_scope() -> None:
    guide = CH05.read_text(encoding="utf-8")

    assert "../ch03/README.md" in guide
    assert "rollback 명령" in guide
    assert "Application 생성" in guide
    assert "cluster sync나 rollback 명령을" not in guide
    assert "publish_model.py candidate-b" not in guide
    assert "TARGET_CONTEXT" not in guide
