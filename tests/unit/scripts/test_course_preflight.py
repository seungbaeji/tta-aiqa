"""Tests for bounded, non-destructive course preflight checks."""

from __future__ import annotations

import argparse
import socket
import stat
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
preflight = import_module("scripts.preflight")


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


def test_kubernetes_context_check_fails_closed_when_expected_is_missing(
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


def test_kubernetes_context_check_rejects_current_context_mismatch(
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


def test_kubernetes_context_check_fails_when_kubectl_is_unavailable(
    monkeypatch,
) -> None:
    def unavailable_command(*_args, **_kwargs):
        raise FileNotFoundError("kubectl")

    monkeypatch.setattr(preflight, "_command", unavailable_command)

    result = preflight.check_kubernetes_context("approved-course-cluster")

    assert result.status == "fail"
    assert result.required is True
    assert "unable to inspect" in result.detail


def test_kubernetes_target_requires_context_and_target_base_url(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def passing_check(*_args, **_kwargs):
        return preflight.Check("stub", "pass", "ok")

    for name in (
        "check_required_paths",
        "check_git_clean",
        "check_disk",
    ):
        monkeypatch.setattr(preflight, name, passing_check)

    args = argparse.Namespace(
        scope="kubernetes-target",
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
    readiness = next(
        check for check in checks if check.name == "target_readiness"
    )

    assert context.status == "fail"
    assert context.required is True
    assert readiness.status == "fail"
    assert readiness.required is True
    assert "requires --target-url" in readiness.detail
    assert preflight.report(checks, "kubernetes-target")["passed"] is False


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


def test_compose_observability_scope_is_a_d1_gate_without_kubernetes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    called: set[str] = set()

    def passing_check(*_args, **_kwargs):
        return preflight.Check("stub", "pass", "ok")

    for name in ("check_required_paths", "check_git_clean", "check_disk"):
        monkeypatch.setattr(preflight, name, passing_check)

    for name in (
        "check_ports",
        "check_docker",
        "check_compose_config",
        "check_secret_directory",
        "check_dashboard_environment",
        "check_traffic_artifact_directory",
    ):
        monkeypatch.setattr(
            preflight,
            name,
            lambda *args, _name=name, **kwargs: (
                called.add(_name)
                or preflight.Check(_name, "pass", "ok")
            ),
        )

    monkeypatch.setattr(
        preflight,
        "check_kubernetes_context",
        lambda _expected: (_ for _ in ()).throw(
            AssertionError("compose scope must not inspect Kubernetes")
        ),
    )

    args = argparse.Namespace(
        scope="compose-observability",
        curriculum_repo=tmp_path,
        allow_dirty=True,
        min_free_gib=0.0,
        expected_context=None,
        target_url=None,
    )

    checks = preflight.run_checks(args)

    assert called == {
        "check_ports",
        "check_docker",
        "check_compose_config",
        "check_secret_directory",
        "check_dashboard_environment",
        "check_traffic_artifact_directory",
    }
    assert preflight.report(checks, args.scope)["passed"] is True


def test_traffic_artifact_smoke_preserves_existing_content_and_mode(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "traffic"
    directory.mkdir(mode=0o750)
    marker = directory / "existing.jsonl"
    secret_content = "learner-evidence-must-not-be-reported"
    marker.write_text(secret_content, encoding="utf-8")
    original_mode = stat.S_IMODE(directory.stat().st_mode)

    result = preflight.check_traffic_artifact_directory(directory)

    assert result.status == "pass"
    assert result.required is True
    assert secret_content not in result.detail
    assert marker.read_text(encoding="utf-8") == secret_content
    assert stat.S_IMODE(directory.stat().st_mode) == original_mode
    assert {path.name for path in directory.iterdir()} == {"existing.jsonl"}


def test_traffic_artifact_smoke_fails_without_leaking_error_content(
    monkeypatch,
    tmp_path: Path,
) -> None:
    directory = tmp_path / "traffic"
    directory.mkdir()
    secret_error = "private-existing-file-name"

    def denied(*_args, **_kwargs):
        raise PermissionError(secret_error)

    monkeypatch.setattr(preflight.tempfile, "mkstemp", denied)

    result = preflight.check_traffic_artifact_directory(directory)

    assert result.status == "fail"
    assert result.required is True
    assert secret_error not in result.detail
    assert not tuple(directory.iterdir())


def test_dashboard_environment_reports_missing_keys_without_secret_values(
    tmp_path: Path,
) -> None:
    secret = "do-not-print-dashboard-token"
    env_path = tmp_path / ".env.grafanacloud"
    env_path.write_text(
        "\n".join(
            (
                "AIQA_GRAFANA_URL=https://course.grafana.net",
                "AIQA_GRAFANA_DASHBOARD_PATH=deploy/grafana.json",
                f"AIQA_GRAFANA_DASHBOARD_TOKEN={secret}",
                "AIQA_GRAFANA_FOLDER_UID=tta-aiqa",
                "AIQA_GRAFANA_METRICS_DATASOURCE_UID=metrics",
                "AIQA_GRAFANA_LOGS_DATASOURCE_UID=logs",
            )
        ),
        encoding="utf-8",
    )
    env_path.chmod(0o600)

    result = preflight.check_dashboard_environment(env_path)

    assert result.status == "fail"
    assert "AIQA_GRAFANA_TRACES_DATASOURCE_UID:missing" in result.detail
    assert secret not in result.detail


def test_dashboard_environment_accepts_private_complete_metadata(
    tmp_path: Path,
) -> None:
    dashboard = tmp_path / "dashboard.json"
    dashboard.write_text("{}", encoding="utf-8")
    env_path = tmp_path / ".env.grafanacloud"
    env_path.write_text(
        "\n".join(
            (
                'AIQA_GRAFANA_URL="https://course.grafana.net"',
                f"AIQA_GRAFANA_DASHBOARD_PATH={dashboard}",
                "AIQA_GRAFANA_DASHBOARD_TOKEN=private-token",
                "AIQA_GRAFANA_FOLDER_UID=tta-aiqa",
                "AIQA_GRAFANA_METRICS_DATASOURCE_UID=metrics",
                "AIQA_GRAFANA_LOGS_DATASOURCE_UID=logs",
                "AIQA_GRAFANA_TRACES_DATASOURCE_UID=traces",
            )
        ),
        encoding="utf-8",
    )
    env_path.chmod(0o600)

    result = preflight.check_dashboard_environment(env_path)

    assert result.status == "pass"
    assert "private-token" not in result.detail


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_required_target_url_uses_base_url_and_injected_opener() -> None:
    opened: list[tuple[str, int]] = []

    def opener(url: str, timeout: int):
        opened.append((url, timeout))
        return _Response()

    result = preflight.check_target_readiness(
        "https://risk.example.test/course-api/",
        required=True,
        open_url=opener,
    )

    assert result.status == "pass"
    assert opened == [
        ("https://risk.example.test/course-api/health/ready", 5)
    ]


def test_required_target_url_rejects_missing_or_non_http_url_without_io() -> None:
    def unexpected_open(*_args, **_kwargs):
        raise AssertionError("invalid URL must fail before network I/O")

    for value in (
        None,
        "",
        "risk.example.test",
        "ftp://risk.example.test",
        "https://risk.example.test/health/ready",
    ):
        result = preflight.check_target_readiness(
            value,
            required=True,
            open_url=unexpected_open,
        )

        assert result.status == "fail"
        assert result.required is True


def test_target_readiness_reports_injected_network_failure() -> None:
    def unavailable(*_args, **_kwargs):
        raise URLError("offline")

    result = preflight.check_target_readiness(
        "https://risk.example.test",
        required=True,
        open_url=unavailable,
    )

    assert result.status == "fail"
    assert "readiness request failed" in result.detail
