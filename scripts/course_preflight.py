"""Run bounded, non-destructive D-1 checks for the course environment."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import stat
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURRICULUM_REPO = ROOT.parent / "ttamlops-2607"
DEFAULT_OUTPUT = ROOT / "artifacts/reports/course-preflight.json"
COMPOSE_DIR = ROOT / "deploy/compose/simple-mlops"
ALLOY_SECRETS = COMPOSE_DIR / "secrets/alloy"
DASHBOARD_ENV = ROOT / ".env.grafanacloud"
TRAFFIC_ARTIFACT_DIRECTORY = ROOT / "artifacts/traffic"
REQUIRED_SECRET_FILES = (
    "metrics-url",
    "metrics-username",
    "logs-url",
    "logs-username",
    "otlp-url",
    "otlp-username",
    "api-key",
)
REQUIRED_DASHBOARD_ENV_KEYS = (
    "AIQA_GRAFANA_URL",
    "AIQA_GRAFANA_DASHBOARD_PATH",
    "AIQA_GRAFANA_DASHBOARD_TOKEN",
    "AIQA_GRAFANA_FOLDER_UID",
    "AIQA_GRAFANA_METRICS_DATASOURCE_UID",
    "AIQA_GRAFANA_LOGS_DATASOURCE_UID",
    "AIQA_GRAFANA_TRACES_DATASOURCE_UID",
)
REQUIRED_LAB_PATHS = (
    "artifacts/models/revisions/v2/deployed/metadata.json",
    "artifacts/models/revisions/v2/deployed/model.joblib",
    "configs/serving/api.yaml",
    "data/splits/physionet-2012/revisions/v2/datasets/operational.csv",
    "deploy/compose/simple-mlops/compose.grafana-cloud.yaml",
    "deploy/compose/simple-mlops/compose.yaml",
    "docs/reference/evidence/incident/initial-signal.json",
    "docs/reference/evidence/incident/prepared-observability-correlation.json",
    "labs/release-decision-record.md",
)
REQUIRED_CURRICULUM_PATHS = (
    "docs/v2/index.md",
    "mkdocs.yml",
    "slide/decks.toml",
    "slide/source/v2-course",
)
COURSE_PORTS = (5000, 8000, 12345)


@dataclass(frozen=True)
class Check:
    """One bounded preflight result with no secret values."""

    name: str
    status: str
    detail: str
    required: bool = True


def _command(command: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def check_required_paths(
    name: str,
    root: Path,
    relative_paths: tuple[str, ...],
) -> Check:
    missing = [
        relative for relative in relative_paths if not (root / relative).exists()
    ]
    if missing:
        return Check(name, "fail", "missing: " + ", ".join(missing))
    return Check(name, "pass", f"{len(relative_paths)} required paths exist")


def check_git_clean(name: str, repo: Path, *, allow_dirty: bool) -> Check:
    result = _command(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        repo,
    )
    if result.returncode != 0:
        return Check(name, "fail", "unable to inspect Git worktree")
    if result.stdout.strip():
        status = "warn" if allow_dirty else "fail"
        return Check(name, status, "uncommitted changes are present")
    return Check(name, "pass", "worktree is clean")


def check_disk(root: Path, minimum_gib: float) -> Check:
    free_gib = shutil.disk_usage(root).free / (1024**3)
    status_value = "pass" if free_gib >= minimum_gib else "fail"
    return Check(
        "free_disk",
        status_value,
        f"{free_gib:.1f} GiB free; minimum {minimum_gib:.1f} GiB",
    )


def check_ports(host: str = "127.0.0.1") -> Check:
    occupied: list[str] = []
    for port in COURSE_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                occupied.append(f"{host}:{port}")
    if occupied:
        return Check(
            "course_ports",
            "fail",
            "already in use before startup: " + ", ".join(occupied),
        )
    return Check("course_ports", "pass", "5000, 8000 and 12345 are available")


def check_docker() -> Check:
    try:
        result = _command(("docker", "info"), ROOT)
    except OSError:
        return Check("docker_daemon", "fail", "docker command is unavailable")
    if result.returncode != 0:
        return Check("docker_daemon", "fail", "docker info failed")
    return Check("docker_daemon", "pass", "Docker daemon is reachable")


def check_compose_config() -> Check:
    try:
        result = _command(
            (
                "docker",
                "compose",
                "-f",
                str(COMPOSE_DIR / "compose.yaml"),
                "-f",
                str(COMPOSE_DIR / "compose.grafana-cloud.yaml"),
                "config",
                "--quiet",
            ),
            ROOT,
        )
    except OSError:
        return Check("compose_config", "fail", "docker compose is unavailable")
    if result.returncode != 0:
        return Check("compose_config", "fail", "docker compose config failed")
    return Check("compose_config", "pass", "base and Grafana override are valid")


def check_secret_directory(directory: Path = ALLOY_SECRETS) -> Check:
    problems: list[str] = []
    for name in REQUIRED_SECRET_FILES:
        path = directory / name
        if not path.is_file():
            problems.append(f"{name}:missing")
            continue
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            problems.append(f"{name}:permissions-{mode:03o}")
        if path.stat().st_size == 0:
            problems.append(f"{name}:empty")
    if problems:
        return Check(
            "alloy_secrets",
            "fail",
            "secret metadata problems: " + ", ".join(problems),
        )
    return Check(
        "alloy_secrets",
        "pass",
        "required files exist, are non-empty, and are not group/world-readable",
    )


def _http_url_is_valid(value: str, *, https_only: bool = False) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value)
        hostname = parsed.hostname
    except ValueError:
        return False
    allowed_schemes = {"https"} if https_only else {"http", "https"}
    return (
        parsed.scheme in allowed_schemes
        and bool(hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
    )


def check_dashboard_environment(path: Path = DASHBOARD_ENV) -> Check:
    """Validate dashboard D-1 metadata without exposing credential values."""
    if not path.is_file():
        return Check(
            "grafana_dashboard_environment",
            "fail",
            ".env.grafanacloud is missing",
        )

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned = value.strip()
        if (
            len(cleaned) >= 2
            and cleaned[0] == cleaned[-1]
            and cleaned[0] in {"'", '"'}
        ):
            cleaned = cleaned[1:-1]
        values[key.strip()] = cleaned

    problems = [
        f"{key}:missing"
        for key in REQUIRED_DASHBOARD_ENV_KEYS
        if not values.get(key)
    ]
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        problems.append(f".env.grafanacloud:permissions-{mode:03o}")
    grafana_url = values.get("AIQA_GRAFANA_URL")
    if grafana_url and not _http_url_is_valid(grafana_url, https_only=True):
        problems.append("AIQA_GRAFANA_URL:invalid-https-url")

    dashboard_path = values.get("AIQA_GRAFANA_DASHBOARD_PATH")
    if dashboard_path:
        resolved = Path(dashboard_path)
        if not resolved.is_absolute():
            resolved = ROOT / resolved
        if not resolved.is_file():
            problems.append("AIQA_GRAFANA_DASHBOARD_PATH:not-found")

    if problems:
        return Check(
            "grafana_dashboard_environment",
            "fail",
            "dashboard metadata problems: " + ", ".join(problems),
        )
    return Check(
        "grafana_dashboard_environment",
        "pass",
        "required dashboard metadata exists; URL is HTTPS",
    )


def check_traffic_artifact_directory(
    directory: Path = TRAFFIC_ARTIFACT_DIRECTORY,
) -> Check:
    """Exercise host bind-mount writes with unique temporary files only."""
    if directory.is_symlink() or not directory.is_dir():
        return Check(
            "traffic_artifact_write",
            "fail",
            "traffic artifact directory is missing, unsafe, or not a directory",
        )

    probes: list[Path] = []
    try:
        target_fd, target_name = tempfile.mkstemp(
            prefix=".aiqa-preflight-",
            suffix=".tmp",
            dir=directory,
        )
        target = Path(target_name)
        probes.append(target)
        with os.fdopen(target_fd, "wb") as stream:
            stream.write(b"create-write-probe\n")
            stream.flush()
            os.fsync(stream.fileno())

        replacement_fd, replacement_name = tempfile.mkstemp(
            prefix=".aiqa-preflight-",
            suffix=".replacement",
            dir=directory,
        )
        replacement = Path(replacement_name)
        probes.append(replacement)
        with os.fdopen(replacement_fd, "wb") as stream:
            stream.write(b"atomic-replace-probe\n")
            stream.flush()
            os.fsync(stream.fileno())

        replacement.replace(target)
        if not target.is_file():
            raise OSError("atomic replacement did not produce a file")
        target.unlink()
        if target.exists():
            raise OSError("temporary probe deletion did not complete")
    except OSError:
        return Check(
            "traffic_artifact_write",
            "fail",
            "temporary create/write/atomic-replace/delete check failed",
        )
    finally:
        for probe in probes:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass

    return Check(
        "traffic_artifact_write",
        "pass",
        "temporary create/write/atomic-replace/delete succeeded; "
        "existing artifact contents were not inspected",
    )


def check_kubernetes_context(expected: str | None) -> Check:
    if not expected:
        return Check(
            "kubernetes_context",
            "fail",
            "kubernetes-target scope requires a non-empty expected context",
        )
    try:
        result = _command(("kubectl", "config", "current-context"), ROOT)
    except OSError:
        return Check(
            "kubernetes_context",
            "fail",
            "unable to inspect the current Kubernetes context",
        )
    current = result.stdout.strip()
    if result.returncode != 0 or current != expected:
        return Check(
            "kubernetes_context",
            "fail",
            f"expected {expected!r}; current context does not match",
        )
    return Check("kubernetes_context", "pass", f"matched {expected!r}")


def check_target_readiness(
    target_url: str | None,
    *,
    required: bool = False,
    open_url: Callable[..., Any] | None = None,
) -> Check:
    """Check an API base URL; append the stable readiness path exactly once."""
    if not target_url:
        if required:
            return Check(
                "target_readiness",
                "fail",
                "kubernetes-target scope requires --target-url "
                "with an HTTP(S) API base URL",
            )
        return Check(
            "target_readiness",
            "skip",
            "no target URL supplied",
            required=False,
        )
    valid_url = _http_url_is_valid(target_url)
    target_path = (
        urllib.parse.urlsplit(target_url).path.rstrip("/")
        if valid_url
        else ""
    )
    if (
        not valid_url
        or target_path.endswith("/health/ready")
    ):
        return Check(
            "target_readiness",
            "fail",
            "--target-url must be an HTTP(S) API base URL without "
            "credentials, query, fragment, or /health/ready",
            required=required,
        )

    url = target_url.rstrip("/") + "/health/ready"
    opener = open_url or urllib.request.urlopen
    try:
        with opener(url, timeout=5) as response:
            if response.status != 200:
                return Check(
                    "target_readiness",
                    "fail",
                    f"readiness returned HTTP {response.status}",
                    required=required,
                )
    except (urllib.error.URLError, TimeoutError, ValueError):
        return Check(
            "target_readiness",
            "fail",
            "readiness request failed",
            required=required,
        )
    return Check(
        "target_readiness",
        "pass",
        "target readiness returned HTTP 200",
        required=required,
    )


def run_checks(args: argparse.Namespace) -> list[Check]:
    curriculum_repo = args.curriculum_repo.resolve()
    checks = [
        check_required_paths("lab_assets", ROOT, REQUIRED_LAB_PATHS),
        check_required_paths(
            "curriculum_assets",
            curriculum_repo,
            REQUIRED_CURRICULUM_PATHS,
        ),
        check_git_clean("lab_git", ROOT, allow_dirty=args.allow_dirty),
        check_git_clean(
            "curriculum_git",
            curriculum_repo,
            allow_dirty=args.allow_dirty,
        ),
        check_disk(ROOT, args.min_free_gib),
    ]
    if args.scope == "compose-observability":
        checks.extend(
            (
                check_ports(),
                check_docker(),
                check_compose_config(),
                check_secret_directory(),
                check_dashboard_environment(),
                check_traffic_artifact_directory(),
            )
        )
    elif args.scope == "kubernetes-target":
        checks.extend(
            (
                check_kubernetes_context(args.expected_context),
                check_target_readiness(args.target_url, required=True),
            )
        )
    return checks


def report(checks: list[Check], scope: str) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "scope": scope,
        "checked_at": datetime.now(tz=UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "passed": not any(
            item.required and item.status == "fail" for item in checks
        ),
        "checks": [asdict(item) for item in checks],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope",
        choices=("static", "compose-observability", "kubernetes-target"),
        default="static",
    )
    parser.add_argument(
        "--curriculum-repo",
        type=Path,
        default=DEFAULT_CURRICULUM_REPO,
    )
    parser.add_argument(
        "--target-url",
        help=(
            "required API base URL for --scope kubernetes-target; "
            "/health/ready is appended"
        ),
    )
    parser.add_argument(
        "--expected-context",
        help="required Kubernetes context for --scope kubernetes-target",
    )
    parser.add_argument("--min-free-gib", type=float, default=3.0)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    checks = run_checks(args)
    result = report(checks, args.scope)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for item in checks:
        print(f"[{item.status.upper():4}] {item.name}: {item.detail}")
    print(f"wrote preflight evidence: {args.output}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
