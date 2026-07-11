"""Markdown report writer for data quality results."""

from __future__ import annotations

from pathlib import Path

from ai_quality.data_quality.domain.quality_report import QualityReport


class MarkdownQualityReportWriter:
    """Write a compact quality report as Markdown."""

    def write(self, report: QualityReport, output_path: Path) -> Path:
        """Write a report and return the output path."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_quality_report(report), encoding="utf-8")
        return output_path


def render_quality_report(report: QualityReport) -> str:
    """Render a quality report in Markdown."""
    lines = [
        "# 1장 데이터 품질 리포트",
        "",
        f"- 행(row) 수: {report.row_count}",
        f"- 컬럼(column) 수: {report.column_count}",
        f"- 누락 필수 컬럼: {', '.join(report.missing_columns) or '없음'}",
        f"- 기본 평가 전제 충족: {report.is_evaluation_ready}",
        "",
        "## 라벨 표본 수(Label Support)",
        "",
        "| 항목 | 건수(count) |",
        "| --- | --- |",
        f"| `{report.label_support.positive_label}` | "
        f"{report.label_support.positive_count} |",
        f"| `{report.label_support.negative_label}` | "
        f"{report.label_support.negative_count} |",
        f"| `invalid` | {report.label_support.invalid_count} |",
        f"| `missing` | {report.label_support.missing_count} |",
        "",
        "## 범위 검증(Range Checks)",
        "",
        "| 컬럼(column) | 범위 초과 건수(invalid_count) | "
        "범위 초과 비율(invalid_ratio) |",
        "| --- | --- | --- |",
    ]

    for result in report.range_results:
        lines.append(
            f"| `{result.column}` | {result.invalid_count} | "
            f"{result.invalid_ratio:.2f}% |"
        )

    lines.append("")
    return "\n".join(lines)
