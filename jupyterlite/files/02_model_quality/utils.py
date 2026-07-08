"""Notebook utilities for course Jupyter and JupyterLite workbooks.

The notebooks should show the QA evidence path, not long package bootstrap
logic. This module keeps Lite/package setup and repeated runtime glue out of
the learner-facing cells.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import sys
from pathlib import Path
from typing import Any

pd: Any | None = None
aiq_lite: Any | None = None

LITE_WHEEL_NAME = "ttamlops_ai_quality_lite-0.1.0-py3-none-any.whl"
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


async def ensure_pandas() -> Any:
    """Import pandas, installing it in JupyterLite when needed."""
    try:
        return importlib.import_module("pandas")
    except ModuleNotFoundError:
        import piplite

        await piplite.install("pandas")
        return importlib.import_module("pandas")


async def ensure_ai_quality_lite() -> Any:
    """Import ai_quality.lite, installing the Lite wheel without js.window."""
    try:
        return importlib.import_module("ai_quality.lite")
    except ModuleNotFoundError:
        pass

    import micropip

    wheel_candidates = [
        f"../files/wheels/{LITE_WHEEL_NAME}",
        f"./files/wheels/{LITE_WHEEL_NAME}",
        f"files/wheels/{LITE_WHEEL_NAME}",
        f"/jupyterlite/files/wheels/{LITE_WHEEL_NAME}",
    ]
    install_errors: list[str] = []
    for wheel_url in wheel_candidates:
        try:
            await micropip.install(wheel_url, deps=False)
            return importlib.import_module("ai_quality.lite")
        except Exception as exc:
            install_errors.append(f"{wheel_url}: {type(exc).__name__}: {exc}")

    raise RuntimeError(
        "ttamlops-ai-quality Lite wheel 설치에 실패했습니다. "
        "확인한 경로: " + " | ".join(install_errors)
    )


async def prepare_notebook() -> PreparedNotebook:
    """Prepare notebook dependencies and expose shared modules."""
    global pd, aiq_lite

    add_course_paths()
    pd = await ensure_pandas()
    aiq_lite = await ensure_ai_quality_lite()
    return PreparedNotebook(pandas=pd, aiq_lite=aiq_lite)
