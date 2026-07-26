"""Tests for bounded, read-only course preflight checks."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
preflight = import_module("scripts.course_preflight")


def test_secret_check_reports_metadata_without_values(tmp_path: Path) -> None:
    secret_value = "do-not-print-this-value"
    for name in preflight.REQUIRED_SECRET_FILES:
        path = tmp_path / name
        path.write_text(secret_value, encoding="utf-8")
        path.chmod(0o600)

    result = preflight.check_secret_directory(tmp_path)

    assert result.status == "pass"
    assert secret_value not in result.detail


def test_secret_check_rejects_missing_or_world_readable_file(
    tmp_path: Path,
) -> None:
    for name in preflight.REQUIRED_SECRET_FILES[:-1]:
        path = tmp_path / name
        path.write_text("secret", encoding="utf-8")
        path.chmod(0o600)
    exposed = tmp_path / preflight.REQUIRED_SECRET_FILES[0]
    exposed.chmod(0o644)

    result = preflight.check_secret_directory(tmp_path)

    assert result.status == "fail"
    assert "permissions-644" in result.detail
    assert f"{preflight.REQUIRED_SECRET_FILES[-1]}:missing" in result.detail


def test_port_check_detects_an_existing_listener(monkeypatch) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        monkeypatch.setattr(preflight, "COURSE_PORTS", (port,))

        result = preflight.check_ports()

    assert result.status == "fail"
    assert str(port) in result.detail


def test_report_fails_only_for_required_failures() -> None:
    result = preflight.report(
        [
            preflight.Check("required", "pass", "ok"),
            preflight.Check("optional", "skip", "not configured", required=False),
        ],
        "static",
    )

    assert result["passed"] is True


def test_live_kubernetes_context_check_fails_closed_when_expected_is_missing(
    monkeypatch,
) -> None:
    def unexpected_command(*_args, **_kwargs):
        raise AssertionError("kubectl must not run without an expected context")

    monkeypatch.setattr(preflight, "_command", unexpected_command)

    for expected in (None, ""):
        result = preflight.check_kubernetes_context(expected)

        assert result.status == "fail"
        assert result.required is True
        assert "requires a non-empty expected context" in result.detail


def test_live_kubernetes_context_check_rejects_current_context_mismatch(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        preflight,
        "_command",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=("kubectl", "config", "current-context"),
            returncode=0,
            stdout="unexpected-cluster\n",
            stderr="",
        ),
    )

    result = preflight.check_kubernetes_context("approved-course-cluster")

    assert result.status == "fail"
    assert result.required is True
    assert "expected 'approved-course-cluster'" in result.detail


def test_live_kubernetes_context_check_fails_when_kubectl_is_unavailable(
    monkeypatch,
) -> None:
    def unavailable_command(*_args, **_kwargs):
        raise FileNotFoundError("kubectl")

    monkeypatch.setattr(preflight, "_command", unavailable_command)

    result = preflight.check_kubernetes_context("approved-course-cluster")

    assert result.status == "fail"
    assert result.required is True
    assert "unable to inspect" in result.detail


def test_live_scope_reports_missing_expected_context_as_required_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def passing_check(*_args, **_kwargs):
        return preflight.Check("stub", "pass", "ok")

    for name in (
        "check_required_paths",
        "check_git_clean",
        "check_disk",
        "check_ports",
        "check_docker",
        "check_compose_config",
        "check_secret_directory",
        "check_target_readiness",
    ):
        monkeypatch.setattr(preflight, name, passing_check)

    args = argparse.Namespace(
        scope="live",
        curriculum_repo=tmp_path,
        allow_dirty=True,
        min_free_gib=0.0,
        expected_context=None,
        target_url=None,
    )

    checks = preflight.run_checks(args)
    context = next(
        check for check in checks if check.name == "kubernetes_context"
    )

    assert context.status == "fail"
    assert context.required is True
    assert preflight.report(checks, "live")["passed"] is False


def test_static_scope_does_not_require_a_kubernetes_context(
    monkeypatch,
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        scope="static",
        curriculum_repo=tmp_path,
        allow_dirty=True,
        min_free_gib=0.0,
        expected_context=None,
        target_url=None,
    )

    def unexpected_context_check(_expected):
        raise AssertionError("static scope must not check Kubernetes context")

    monkeypatch.setattr(
        preflight,
        "check_kubernetes_context",
        unexpected_context_check,
    )

    checks = preflight.run_checks(args)

    assert all(check.name != "kubernetes_context" for check in checks)
