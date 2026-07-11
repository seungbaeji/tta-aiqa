"""Notebook utilities for chapter 1 data-quality workbook.

The notebook should teach the evidence path, not hide long helper logic in
cells. This module keeps the display tables thin while using the browser-safe
`ai_quality.lite` package as the shared course contract.
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

DATA_PATH = "data/vital_signs_evaluation_baseline.csv"
MIN_CLASS_SUPPORT = 30


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
        add_once(base / "01_data_quality")
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


@dataclass(frozen=True)
class ChapterOneContext:
    """Loaded data and provenance for chapter 1 workbook cells."""

    dataframe: pd.DataFrame
    data_source: str
    execution_scope: str
    provenance: pd.DataFrame
    preview: pd.DataFrame
    label_distribution: pd.DataFrame


def percent(count: int, total: int) -> float:
    """Return a rounded percentage."""
    return round((count / total * 100.0), 2) if total else 0.0


def role_for_column(column: str) -> str:
    """Return the QA role of a column."""
    if column in aiq_lite.FEATURE_COLUMNS:
        return "feature"
    if column == "label":
        return "label"
    if column in {"patient_id", "timestamp"}:
        return "traceability"
    return "supporting"


def dtype_expectation(column: str) -> str:
    """Return the workbook-level type expectation for a column."""
    if column in aiq_lite.FEATURE_COLUMNS:
        return "numeric"
    if column == "timestamp":
        return "parseable_datetime"
    if column == "label":
        return "allowed_label"
    return "identifier_or_supporting"


def observed_dtype_status(dataframe: pd.DataFrame, column: str) -> str:
    """Return a QA-oriented observed dtype status."""
    if column not in dataframe.columns:
        return "missing"
    if column in aiq_lite.FEATURE_COLUMNS:
        numeric_values = pd.to_numeric(dataframe[column], errors="coerce")
        return "numeric_like" if numeric_values.notna().any() else "not_numeric"
    if column == "timestamp":
        parsed = pd.to_datetime(dataframe[column], errors="coerce")
        return "parseable" if parsed.notna().any() else "not_parseable"
    if column == "label":
        labels = dataframe[column].map(aiq_lite.normalize_label)
        allowed = labels.isin([aiq_lite.POSITIVE_LABEL, aiq_lite.NEGATIVE_LABEL])
        return "allowed_labels" if bool(allowed.all()) else "unexpected_label"
    return str(dataframe[column].dtype)


def build_schema_gate(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build the required-column and dtype gate."""
    rows: list[dict[str, object]] = []
    for column in aiq_lite.REQUIRED_COLUMNS:
        rows.append(
            {
                "column": column,
                "role": role_for_column(column),
                "required": True,
                "exists": column in dataframe.columns,
                "expected": dtype_expectation(column),
                "observed": observed_dtype_status(dataframe, column),
            }
        )
    return pd.DataFrame(rows)


def summarize_schema_gate(schema_gate: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return schema decision and missing column list."""
    missing_columns = schema_gate.loc[~schema_gate["exists"], "column"].tolist()
    problem_rows = schema_gate.loc[
        (~schema_gate["exists"])
        | schema_gate["observed"].isin(
            ["not_numeric", "not_parseable", "unexpected_label"]
        )
    ]
    decision = pd.DataFrame(
        [
            {
                "gate": "schema_gate",
                "status": "fail" if len(problem_rows) else "pass",
                "problem_count": len(problem_rows),
                "qa_judgment": "필수 컬럼과 기본 타입 계약을 만족합니다."
                if problem_rows.empty
                else "필수 컬럼 또는 타입 문제가 있어 데이터 추출 기준 확인이 필요합니다.",
            }
        ]
    )
    return decision, missing_columns


def build_missing_gate(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build the missing-value gate for required columns."""
    rows: list[dict[str, object]] = []
    total = len(dataframe)
    for column in aiq_lite.REQUIRED_COLUMNS:
        if column not in dataframe.columns:
            rows.append(
                {
                    "column": column,
                    "role": role_for_column(column),
                    "missing_count": total,
                    "missing_ratio_pct": 100.0 if total else 0.0,
                    "gate": "fail_missing_column",
                }
            )
            continue
        missing_count = int(dataframe[column].isna().sum())
        rows.append(
            {
                "column": column,
                "role": role_for_column(column),
                "missing_count": missing_count,
                "missing_ratio_pct": percent(missing_count, total),
                "gate": "pass" if missing_count == 0 else "review",
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["missing_count", "column"], ascending=[False, True]
    )


def build_missing_label_impact(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Show which labels are affected by required-column missing values."""
    available_required = [
        column for column in aiq_lite.REQUIRED_COLUMNS if column in dataframe.columns
    ]
    if not available_required:
        return pd.DataFrame(
            [{"label": "not_available", "affected_rows": len(dataframe), "share_pct": 100.0}]
        )
    affected = dataframe[dataframe[available_required].isna().any(axis=1)]
    if affected.empty:
        return pd.DataFrame(
            [{"label": "no_required_missing_rows", "affected_rows": 0, "share_pct": 0.0}]
        )
    counts = affected["label"].map(aiq_lite.normalize_label).value_counts(dropna=False)
    return pd.DataFrame(
        [
            {
                "label": str(label),
                "affected_rows": int(count),
                "share_pct": percent(int(count), len(affected)),
            }
            for label, count in counts.items()
        ]
    )


def summarize_missing_gate(
    dataframe: pd.DataFrame, missing_gate: pd.DataFrame
) -> tuple[pd.DataFrame, int, int, int]:
    """Return missing gate decision and key counts."""
    missing_problem_count = int(missing_gate["missing_count"].sum())
    label_missing_count = (
        int(dataframe["label"].isna().sum()) if "label" in dataframe.columns else len(dataframe)
    )
    feature_missing_count = int(
        missing_gate.loc[missing_gate["role"] == "feature", "missing_count"].sum()
    )
    status = "pass"
    if missing_problem_count > 0:
        status = "review" if label_missing_count == 0 else "fail"
    decision = pd.DataFrame(
        [
            {
                "gate": "missing_gate",
                "status": status,
                "feature_missing_count": feature_missing_count,
                "label_missing_count": label_missing_count,
                "qa_judgment": "필수 입력과 라벨 결측이 없어 결측으로 인한 평가 전제 훼손 가능성은 낮습니다."
                if missing_problem_count == 0
                else "결측 위치와 라벨 집중도를 확인하고 평가 제외 또는 보정 기준을 정해야 합니다.",
            }
        ]
    )
    return decision, missing_problem_count, feature_missing_count, label_missing_count


def build_range_gate(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build the allowed-range gate from ai-quality Lite rules."""
    rows: list[dict[str, object]] = []
    total = len(dataframe)
    for column, (minimum, maximum) in aiq_lite.VALID_RANGES.items():
        if column not in dataframe.columns:
            rows.append(
                {
                    "column": column,
                    "role": role_for_column(column),
                    "min_value": minimum,
                    "max_value": maximum,
                    "invalid_count": 0,
                    "invalid_ratio_pct": 0.0,
                    "gate": "not_in_dataset",
                }
            )
            continue
        values = pd.to_numeric(dataframe[column], errors="coerce")
        invalid_mask = values.notna() & ((values < minimum) | (values > maximum))
        invalid_count = int(invalid_mask.sum())
        rows.append(
            {
                "column": column,
                "role": role_for_column(column),
                "min_value": minimum,
                "max_value": maximum,
                "invalid_count": invalid_count,
                "invalid_ratio_pct": percent(invalid_count, total),
                "gate": "pass" if invalid_count == 0 else "review",
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["invalid_count", "column"], ascending=[False, True]
    )


def build_range_label_impact(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Show label impact for allowed-range violations."""
    rows: list[dict[str, object]] = []
    for column, (minimum, maximum) in aiq_lite.VALID_RANGES.items():
        if column not in dataframe.columns:
            continue
        values = pd.to_numeric(dataframe[column], errors="coerce")
        invalid_mask = values.notna() & ((values < minimum) | (values > maximum))
        if not bool(invalid_mask.any()):
            continue
        counts = (
            dataframe.loc[invalid_mask, "label"]
            .map(aiq_lite.normalize_label)
            .value_counts(dropna=False)
        )
        for label, count in counts.items():
            rows.append(
                {"column": column, "label": str(label), "invalid_count": int(count)}
            )
    if not rows:
        return pd.DataFrame(
            [{"column": "no_range_violation", "label": "not_applicable", "invalid_count": 0}]
        )
    return pd.DataFrame(rows)


def summarize_range_gate(range_gate: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Return range gate decision and key counts."""
    invalid_value_total = int(range_gate["invalid_count"].sum())
    invalid_feature_total = int(
        range_gate.loc[range_gate["role"] == "feature", "invalid_count"].sum()
    )
    decision = pd.DataFrame(
        [
            {
                "gate": "range_gate",
                "status": "review" if invalid_value_total else "pass",
                "invalid_feature_total": invalid_feature_total,
                "invalid_value_total": invalid_value_total,
                "qa_judgment": "허용 범위 초과가 없어 명백한 입력 범위 오류 가능성은 낮습니다."
                if invalid_value_total == 0
                else "허용 범위 초과 값이 있어 수집 단위, 파싱, 오류 코드 유입 확인이 필요합니다.",
            }
        ]
    )
    return decision, invalid_feature_total, invalid_value_total


def build_label_gate(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build label support gate for allowed labels."""
    labels = dataframe["label"].map(aiq_lite.normalize_label)
    total = len(labels)
    counts = labels.value_counts(dropna=False)
    allowed = {aiq_lite.POSITIVE_LABEL, aiq_lite.NEGATIVE_LABEL}
    rows: list[dict[str, object]] = []
    for label, count in counts.items():
        label_text = str(label)
        rows.append(
            {
                "label": label_text,
                "count": int(count),
                "ratio_pct": percent(int(count), total),
                "allowed": label_text in allowed,
                "meets_min_support": int(count) >= MIN_CLASS_SUPPORT
                if label_text in allowed
                else False,
            }
        )
    for expected_label in [aiq_lite.POSITIVE_LABEL, aiq_lite.NEGATIVE_LABEL]:
        if expected_label not in counts.index:
            rows.append(
                {
                    "label": expected_label,
                    "count": 0,
                    "ratio_pct": 0.0,
                    "allowed": True,
                    "meets_min_support": False,
                }
            )
    return pd.DataFrame(rows).sort_values("label")


def summarize_label_gate(
    label_gate: pd.DataFrame,
) -> tuple[pd.DataFrame, int, int, int, bool]:
    """Return label gate decision and support counts."""
    invalid_label_count = int(label_gate.loc[~label_gate["allowed"], "count"].sum())
    positive_support = int(
        label_gate.loc[label_gate["label"] == aiq_lite.POSITIVE_LABEL, "count"].sum()
    )
    negative_support = int(
        label_gate.loc[label_gate["label"] == aiq_lite.NEGATIVE_LABEL, "count"].sum()
    )
    support_problem = (
        positive_support < MIN_CLASS_SUPPORT or negative_support < MIN_CLASS_SUPPORT
    )
    has_problem = invalid_label_count > 0 or support_problem
    decision = pd.DataFrame(
        [
            {
                "gate": "label_gate",
                "status": "fail" if has_problem else "pass",
                "positive_support": positive_support,
                "negative_support": negative_support,
                "invalid_label_count": invalid_label_count,
                "qa_judgment": "허용 라벨과 최소 class support를 만족해 모델 지표 해석으로 넘어갈 수 있습니다."
                if not has_problem
                else "라벨 기준 또는 class support가 부족해 모델 지표 해석 전 재확인이 필요합니다.",
            }
        ]
    )
    return decision, positive_support, negative_support, invalid_label_count, support_problem


def build_evidence_packet(
    *,
    context: ChapterOneContext,
    schema_decision: pd.DataFrame,
    missing_decision: pd.DataFrame,
    range_decision: pd.DataFrame,
    label_decision: pd.DataFrame,
    missing_columns: list[str],
    missing_problem_count: int,
    feature_missing_count: int,
    label_missing_count: int,
    invalid_feature_total: int,
    invalid_value_total: int,
    positive_support: int,
    negative_support: int,
    invalid_label_count: int,
    support_problem: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """Build report-ready evidence packet and handoff table."""
    gate_summary = pd.DataFrame(
        [
            _gate_row(
                "schema_gate",
                str(schema_decision.loc[0, "status"]),
                f"missing_columns={missing_columns}, problem_count={int(schema_decision.loc[0, 'problem_count'])}",
                str(schema_decision.loc[0, "qa_judgment"]),
                "Data Engineering" if missing_columns else "QA",
                "누락이 있으면 데이터 추출 기준을 확인합니다."
                if missing_columns
                else "결측과 범위 gate 근거를 함께 첨부합니다.",
            ),
            _gate_row(
                "missing_gate",
                str(missing_decision.loc[0, "status"]),
                f"feature_missing={feature_missing_count}, label_missing={label_missing_count}",
                str(missing_decision.loc[0, "qa_judgment"]),
                "Data Engineering" if missing_problem_count else "QA",
                "결측 위치와 라벨 집중도를 확인합니다."
                if missing_problem_count
                else "2장 metric 해석 시 결측 제한은 낮게 기록합니다.",
            ),
            _gate_row(
                "range_gate",
                str(range_decision.loc[0, "status"]),
                f"invalid_feature_total={invalid_feature_total}, invalid_value_total={invalid_value_total}",
                str(range_decision.loc[0, "qa_judgment"]),
                "Data Engineering" if invalid_value_total else "QA",
                "소스 시스템과 단위 변환을 확인합니다."
                if invalid_value_total
                else "운영 입력 분포 변화는 5장에서 별도 확인합니다.",
            ),
            _gate_row(
                "label_gate",
                str(label_decision.loc[0, "status"]),
                f"{aiq_lite.POSITIVE_LABEL}={positive_support}, {aiq_lite.NEGATIVE_LABEL}={negative_support}, invalid_label={invalid_label_count}",
                str(label_decision.loc[0, "qa_judgment"]),
                "Labeling/Data Engineering"
                if invalid_label_count or support_problem
                else "QA",
                "라벨 생성 기준과 평가 범위를 확인합니다."
                if invalid_label_count or support_problem
                else "2장에서 Precision/Recall을 class support와 함께 해석합니다.",
            ),
        ]
    )

    fail_gates = gate_summary.loc[gate_summary["status"] == "fail", "gate"].tolist()
    review_gates = gate_summary.loc[gate_summary["status"] == "review", "gate"].tolist()

    if fail_gates:
        final_decision = "hold_for_data_recheck"
        decision_reason = "필수 구조 또는 라벨 기준 문제가 있어 모델 지표 해석을 보류합니다."
    elif review_gates:
        final_decision = "conditional_model_evaluation"
        decision_reason = "검토 항목은 있으나 제한 사항을 명시하면 모델 지표 계산은 가능합니다."
    else:
        final_decision = "ready_for_model_evaluation"
        decision_reason = "데이터 구조, 결측, 범위, 라벨 기준이 모델 평가 전제를 충족합니다."

    evidence_packet = pd.concat(
        [
            pd.DataFrame(
                [
                    {
                        "evidence": "data_provenance",
                        "observed": (
                            f"{context.execution_scope}, rows={len(context.dataframe)}, "
                            f"columns={len(context.dataframe.columns)}"
                        ),
                        "qa_judgment": "데이터 출처와 규모를 보고서에 남길 수 있습니다.",
                        "owner": "QA",
                        "next_action": "2장 모델 평가에서 같은 데이터 범위를 명시합니다.",
                    }
                ]
            ),
            gate_summary.rename(
                columns={"gate": "evidence", "key_observation": "observed"}
            )[["evidence", "observed", "qa_judgment", "owner", "next_action"]],
        ],
        ignore_index=True,
    )

    handoff = pd.DataFrame(
        [
            {
                "chapter": "01_data_quality",
                "decision": final_decision,
                "decision_reason": decision_reason,
                "open_candidates": ", ".join(fail_gates + review_gates)
                if (fail_gates or review_gates)
                else "none",
                "next_chapter_question": (
                    "모델 지표 변화가 threshold, FP/FN, 데이터 조건 변화 중 "
                    "어디와 연결되는가?"
                ),
            }
        ]
    )
    report_sentence = (
        f"1장 데이터 품질 확인 결과, {context.execution_scope} 기준 "
        f"rows={len(context.dataframe)}, {aiq_lite.POSITIVE_LABEL} support={positive_support}, "
        f"{aiq_lite.NEGATIVE_LABEL} support={negative_support}입니다. "
        f"필수 컬럼 누락은 {len(missing_columns)}건, 모델 입력 결측은 {feature_missing_count}건, "
        f"라벨 결측은 {label_missing_count}건, 허용 범위 초과는 {invalid_value_total}건입니다. "
        f"따라서 현재 판단은 {final_decision}이며, 근거는 {decision_reason}"
    )
    return gate_summary, evidence_packet, handoff, report_sentence


def numeric_profile(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return numeric profile for range-gate context."""
    columns = [column for column in aiq_lite.VALID_RANGES if column in dataframe.columns]
    return dataframe.loc[:, columns].describe().T


def _gate_row(
    gate: str,
    status: str,
    key_observation: str,
    qa_judgment: str,
    owner: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "gate": gate,
        "status": status,
        "key_observation": key_observation,
        "qa_judgment": qa_judgment,
        "owner": owner,
        "next_action": next_action,
    }
