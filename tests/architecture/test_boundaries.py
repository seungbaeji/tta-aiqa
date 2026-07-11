"""Executable monorepo and Clean Architecture boundaries."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAMES = {
    "aiqa_core",
    "aiqa_data",
    "aiqa_model",
    "aiqa_observability",
    "aiqa_qa",
    "aiqa_serving",
}
APP_NAMES = {
    "data_quality_pipeline",
    "grafana_dashboard_importer",
    "model_trainer",
    "risk_api",
    "traffic_generator",
}
APP_FOLDERS = {
    "data-quality-pipeline": "data_quality_pipeline",
    "grafana-dashboard-importer": "grafana_dashboard_importer",
    "model-trainer": "model_trainer",
    "risk-api": "risk_api",
    "traffic-generator": "traffic_generator",
}
PACKAGE_LAYERS = {
    "aiqa_core": {"domain", "adapters"},
    "aiqa_data": {"domain", "application", "ports", "adapters"},
    "aiqa_model": {"domain", "application", "ports", "adapters"},
    "aiqa_observability": {"domain", "adapters"},
    "aiqa_qa": {"domain", "application", "adapters"},
    "aiqa_serving": {"domain", "application", "ports", "adapters"},
}
FRAMEWORK_ROOTS = {
    "fastapi",
    "joblib",
    "mlflow",
    "numpy",
    "pandas",
    "pydantic",
    "pydantic_settings",
    "requests",
    "sklearn",
    "yaml",
}


def python_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def project_dependencies(path: Path) -> set[str]:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    dependencies = document["project"].get("dependencies", [])
    return {
        dependency.split("[", 1)[0]
        .split("<", 1)[0]
        .split(">", 1)[0]
        .split("=", 1)[0]
        .strip()
        for dependency in dependencies
    }


@pytest.mark.architecture
def test_workspace_contains_only_v2_members() -> None:
    document = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert set(document["tool"]["uv"]["workspace"]["members"]) == {
        "apps/data-quality-pipeline",
        "apps/grafana-dashboard-importer",
        "apps/model-trainer",
        "apps/risk-api",
        "apps/traffic-generator",
        "packages/aiqa-core",
        "packages/aiqa-data",
        "packages/aiqa-model",
        "packages/aiqa-observability",
        "packages/aiqa-qa",
        "packages/aiqa-serving",
    }


@pytest.mark.architecture
def test_packages_have_only_non_empty_declared_layers() -> None:
    for package, expected_layers in sorted(PACKAGE_LAYERS.items()):
        source = ROOT / "packages" / package.replace("_", "-") / "src" / package
        assert source.is_dir()
        actual_layers = {
            layer
            for layer in ("domain", "application", "ports", "adapters")
            if (source / layer).is_dir()
            and any((source / layer).rglob("*.py"))
        }
        assert actual_layers == expected_layers, package
        for layer in expected_layers:
            modules = list((source / layer).rglob("*.py"))
            assert any(path.name != "__init__.py" for path in modules), (package, layer)


@pytest.mark.architecture
def test_bounded_contexts_depend_only_on_aiqa_core() -> None:
    for pyproject in sorted((ROOT / "packages").glob("*/pyproject.toml")):
        aiqa_dependencies = {
            name for name in project_dependencies(pyproject) if name.startswith("aiqa-")
        }
        expected = set() if pyproject.parent.name == "aiqa-core" else {"aiqa-core"}
        assert aiqa_dependencies == expected, pyproject


@pytest.mark.architecture
def test_domain_and_application_layers_do_not_import_frameworks_or_adapters() -> None:
    failures: list[str] = []
    for path in sorted((ROOT / "packages").glob("*/src/*/**/*.py")):
        if not ({"domain", "application"} & set(path.parts)):
            continue
        imports = python_imports(path)
        forbidden = {
            name
            for name in imports
            if name.split(".", 1)[0] in FRAMEWORK_ROOTS or ".adapters" in name
        }
        if forbidden:
            failures.append(f"{path.relative_to(ROOT)}: {sorted(forbidden)}")
    assert not failures, "\n".join(failures)


@pytest.mark.architecture
def test_active_code_never_imports_legacy_or_another_app() -> None:
    failures: list[str] = []
    active_paths = [ROOT / "apps", ROOT / "packages", ROOT / "scripts"]
    for base in active_paths:
        for path in sorted(base.glob("**/*.py")):
            imports = python_imports(path)
            roots = {name.split(".", 1)[0] for name in imports}
            own_app = next(
                (
                    module
                    for folder, module in APP_FOLDERS.items()
                    if folder in path.parts
                ),
                None,
            )
            forbidden_apps = APP_NAMES - ({own_app} if own_app else set())
            forbidden = ({"legacy"} | forbidden_apps) & roots
            if forbidden:
                failures.append(f"{path.relative_to(ROOT)}: {sorted(forbidden)}")
    assert not failures, "\n".join(failures)
