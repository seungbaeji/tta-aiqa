"""Notebook utilities for course Jupyter and JupyterLite workbooks.

The notebooks should show the QA evidence path, not long package bootstrap
logic. This module keeps Lite/package setup and repeated runtime glue out of
the learner-facing cells.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
import sys
from pathlib import Path
from typing import Any

pd: Any | None = None
aiq_lite: Any | None = None

LITE_NAMES = [
    "FEATURE_COLUMNS",
    "NEGATIVE_LABEL",
    "POSITIVE_LABEL",
    "REQUIRED_COLUMNS",
    "THRESHOLD",
    "VALID_RANGES",
    "compare_input_distribution",
    "compare_snapshots",
    "confusion_from_scores",
    "evaluate_release",
    "generate_events",
    "load_csv_or_sample",
    "metric_row",
    "normalize_label",
    "openapi_contract",
    "post_predict",
    "quality_snapshot",
    "render_prometheus",
    "sample_vital_signs",
    "score_distribution_comparison",
    "score_rows",
    "serving_payload",
    "threshold_table",
    "trace_candidates",
    "validate_payload",
]


@dataclass(frozen=True)
class PreparedNotebook:
    """Runtime modules prepared for local Jupyter and JupyterLite."""

    pandas: Any
    aiq_lite: Any


def add_once(path: Path) -> None:
    """Add an existing path to sys.path once."""
    path_text = str(path)
    if path.exists() and path_text not in sys.path:
        sys.path.insert(0, path_text)


def add_course_paths() -> None:
    """Expose local package and chapter utils paths when running outside Lite."""
    for base in [Path.cwd(), *Path.cwd().parents]:
        add_once(base / "packages" / "ai-quality" / "src")
        add_once(base / "labs" / "ch01_data_quality")
        add_once(base / "labs" / "ch02_model_quality")
        add_once(base / "labs" / "ch03_serving")
        add_once(base / "labs" / "ch04_observability")
        add_once(base / "labs" / "ch05_qa_strategy")
        add_once(base / "01_data_quality")
        add_once(base / "02_model_quality")
        add_once(base / "03_serving")
        add_once(base / "04_observability")
        add_once(base / "05_qa_strategy")
    add_once(Path.cwd())


def resolve_course_path(relative_path: str) -> Path:
    """Find a course file from local repo root or JupyterLite files root."""
    for base in [Path.cwd(), *Path.cwd().parents]:
        candidate = base / relative_path
        if candidate.exists():
            return candidate
    raise FileNotFoundError(relative_path)


def read_json_artifact(relative_path: str) -> Any:
    """Read a small JSON artifact used as prepared notebook evidence."""
    return json.loads(resolve_course_path(relative_path).read_text(encoding="utf-8"))


def read_first_json_artifact(relative_paths: list[str]) -> Any:
    """Read the first available JSON artifact from local/Lite path candidates."""
    errors: list[str] = []
    for relative_path in relative_paths:
        try:
            return read_json_artifact(relative_path)
        except FileNotFoundError as exc:
            errors.append(str(exc))
    raise FileNotFoundError(" | ".join(errors))


def read_text_artifact(relative_path: str) -> str:
    """Read a small text artifact used as prepared notebook evidence."""
    return resolve_course_path(relative_path).read_text(encoding="utf-8")


async def ensure_pandas() -> Any:
    """Import pandas from the local lab environment."""
    try:
        return importlib.import_module("pandas")
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "pandas가 없습니다. 로컬 실습 환경에서는 notebook 안에서 패키지를 설치하지 말고 "
            "`uv sync --group lab` 또는 강의 환경 준비 명령을 실행하세요."
        ) from error


async def ensure_yaml() -> Any:
    """Import PyYAML from the local lab environment."""
    try:
        return importlib.import_module("yaml")
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "PyYAML이 없습니다. 로컬 실습 환경에서는 notebook 안에서 패키지를 설치하지 말고 "
            "`uv sync --group lab` 또는 강의 환경 준비 명령을 실행하세요."
        ) from error


async def ensure_ai_quality_lite() -> Any:
    """Import ai_quality.lite from the local package path."""
    try:
        return importlib.import_module("ai_quality.lite")
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "ai_quality.lite를 찾지 못했습니다. repo root에서 notebook을 실행하거나 "
            "`uv sync --group lab`로 로컬 package 경로를 준비하세요."
        ) from error


async def prepare_notebook() -> PreparedNotebook:
    """Prepare notebook dependencies and expose shared modules."""
    global pd, aiq_lite

    add_course_paths()
    pd = await ensure_pandas()
    aiq_lite = await ensure_ai_quality_lite()
    return PreparedNotebook(pandas=pd, aiq_lite=aiq_lite)
