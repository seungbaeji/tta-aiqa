"""Artifact writer for chapter 2 Great Expectations demo outputs."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_quality.data_quality.domain.validation_result import ValidationResult


@dataclass(frozen=True)
class GreatExpectationsDemoArtifacts:
    """Paths generated for the instructor demo."""

    expectations_path: Path
    validation_result_path: Path
    validation_summary_path: Path
    data_docs_path: Path


def write_great_expectations_demo_artifacts(
    expectations: Sequence[Mapping[str, Any]],
    validation_result: ValidationResult,
    output_dir: Path,
) -> GreatExpectationsDemoArtifacts:
    """Write expectation suite, validation result, summary, and HTML docs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = GreatExpectationsDemoArtifacts(
        expectations_path=output_dir / "chapter_02_expectations.json",
        validation_result_path=output_dir / "chapter_02_validation_result.json",
        validation_summary_path=output_dir / "chapter_02_validation_summary.md",
        data_docs_path=output_dir / "chapter_02_data_docs.html",
    )

    artifacts.expectations_path.write_text(
        json.dumps({"expectations": list(expectations)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    artifacts.validation_result_path.write_text(
        json.dumps(
            serialize_validation_result(validation_result),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    artifacts.validation_summary_path.write_text(
        render_validation_summary(validation_result),
        encoding="utf-8",
    )
    artifacts.data_docs_path.write_text(
        render_data_docs_html(validation_result),
        encoding="utf-8",
    )
    return artifacts


def serialize_validation_result(validation_result: ValidationResult) -> dict[str, Any]:
    """Return a JSON payload including computed summary fields."""
    payload = asdict(validation_result)
    payload["success"] = validation_result.success
    payload["success_count"] = validation_result.success_count
    payload["failure_count"] = validation_result.failure_count
    return payload


def render_validation_summary(validation_result: ValidationResult) -> str:
    """Render a Markdown summary for QA review."""
    lines = [
        "# 2장 데이터 검증 요약",
        "",
        f"- 데이터셋: {validation_result.dataset_name}",
        f"- 행(row) 수: {validation_result.row_count}",
        f"- 전체 성공 여부: {validation_result.success}",
        f"- 통과 기대 조건: {validation_result.success_count}",
        f"- 실패 기대 조건: {validation_result.failure_count}",
        "",
        "| 기대 조건(expectation) | 컬럼(column) | 성공 여부 | 실패 건수 | "
        "실패 비율 | QA 사유 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in validation_result.expectation_results:
        lines.append(
            f"| `{result.expectation_type}` | `{result.column}` | "
            f"{result.success} | {result.unexpected_count} | "
            f"{result.unexpected_ratio:.2f}% | {result.qa_reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_data_docs_html(validation_result: ValidationResult) -> str:
    """Render a compact HTML page similar to a Data Docs review page."""
    rows = []
    for result in validation_result.expectation_results:
        status = "통과" if result.success else "실패"
        rows.append(
            "<tr>"
            f"<td>{html.escape(status)}</td>"
            f"<td>{html.escape(result.expectation_type)}</td>"
            f"<td>{html.escape(result.column)}</td>"
            f"<td>{result.unexpected_count}</td>"
            f"<td>{result.unexpected_ratio:.2f}%</td>"
            f"<td>{html.escape(result.observed_value)}</td>"
            f"<td>{html.escape(result.qa_reason)}</td>"
            "</tr>"
        )

    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"ko\">",
            "<head>",
            "  <meta charset=\"utf-8\">",
            "  <title>2장 데이터 검증 문서</title>",
            "  <style>",
            "    body { font-family: sans-serif; margin: 32px; }",
            "    table { border-collapse: collapse; width: 100%; }",
            "    th, td { border: 1px solid #ccc; padding: 8px; }",
            "    th { background: #f3f4f6; text-align: left; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <h1>2장 데이터 검증 문서</h1>",
            f"  <p>데이터셋: {html.escape(validation_result.dataset_name)}</p>",
            f"  <p>행(row) 수: {validation_result.row_count}</p>",
            f"  <p>전체 성공 여부: {validation_result.success}</p>",
            "  <table>",
            "    <thead>",
            "      <tr>",
            "        <th>상태</th>",
            "        <th>기대 조건(expectation)</th>",
            "        <th>컬럼(column)</th>",
            "        <th>실패 건수</th>",
            "        <th>실패 비율</th>",
            "        <th>관측값</th>",
            "        <th>QA 사유</th>",
            "      </tr>",
            "    </thead>",
            "    <tbody>",
            *rows,
            "    </tbody>",
            "  </table>",
            "</body>",
            "</html>",
            "",
        ]
    )
