"""Run read-only D-1 checks for the AI quality course environment."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import stat
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURRICULUM_REPO = ROOT.parent / "ttamlops-2607"
DEFAULT_OUTPUT = ROOT / "artifacts/reports/course-preflight.json"
COMPOSE_DIR = ROOT / "deploy/compose/simple-mlops"
ALLOY_SECRETS = COMPOSE_DIR / "secrets/alloy"
REQUIRED_SECRET_FILES = (
    "metrics-url",
    "metrics-username",
    "logs-url",
    "logs-username",
    "otlp-url",
    "otlp-username",
    "api-key",
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
    result = _command(("docker", "info"), ROOT)
    if result.returncode != 0:
        return Check("docker_daemon", "fail", "docker info failed")
    return Check("docker_daemon", "pass", "Docker daemon is reachable")


def check_compose_config() -> Check:
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


def check_kubernetes_context(expected: str | None) -> Check:
    if not expected:
        return Check(
            "kubernetes_context",
            "fail",
            "live scope requires a non-empty expected context",
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


def check_target_readiness(target_url: str | None) -> Check:
    if target_url is None:
        return Check(
            "target_readiness",
            "skip",
            "no target URL supplied",
            required=False,
        )
    url = target_url.rstrip("/") + "/health/ready"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status != 200:
                return Check(
                    "target_readiness",
                    "fail",
                    f"readiness returned HTTP {response.status}",
                )
    except (urllib.error.URLError, TimeoutError, ValueError):
        return Check("target_readiness", "fail", "readiness request failed")
    return Check("target_readiness", "pass", "target readiness returned HTTP 200")


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
    if args.scope == "live":
        checks.extend(
            (
                check_ports(),
                check_docker(),
                check_compose_config(),
                check_secret_directory(),
                check_kubernetes_context(args.expected_context),
                check_target_readiness(args.target_url),
            )
        )
    return checks


def report(checks: list[Check], scope: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
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
    parser.add_argument("--scope", choices=("static", "live"), default="static")
    parser.add_argument(
        "--curriculum-repo",
        type=Path,
        default=DEFAULT_CURRICULUM_REPO,
    )
    parser.add_argument("--target-url")
    parser.add_argument(
        "--expected-context",
        help="required, non-empty Kubernetes context for --scope live",
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
