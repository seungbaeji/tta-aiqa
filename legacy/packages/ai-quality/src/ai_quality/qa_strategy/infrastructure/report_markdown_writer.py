"""Markdown writers for Chapter 5 QA strategy artifacts."""

from __future__ import annotations

from pathlib import Path

from ai_quality.data_quality.domain.quality_report import LabelSupport
from ai_quality.qa_strategy.domain.approval_rule import ApprovalDecision
from ai_quality.qa_strategy.domain.drift_signal import (
    FeatureDistributionComparison,
    ScoreDistributionComparison,
)
from ai_quality.qa_strategy.domain.quality_issue import IssueTraceReport


def render_drift_report_markdown(
    feature_comparisons: list[FeatureDistributionComparison],
    score_comparison: ScoreDistributionComparison,
) -> str:
    """Render drift and prediction distribution report."""
    lines = [
        "# Drift Report",
        "",
        "## Input Distribution",
        "",
        "| feature | baseline_mean | current_mean | delta | delta_ratio | shifted |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in feature_comparisons:
        lines.append(
            "| "
            f"{item.feature} | "
            f"{item.baseline_mean:.4f} | "
            f"{item.current_mean:.4f} | "
            f"{item.mean_delta:.4f} | "
            f"{item.mean_delta_ratio:.4f} | "
            f"{item.shifted} |"
        )

    lines.extend(
        [
            "",
            "## Input Distribution Buckets",
            "",
            "| feature | bin | baseline_count | current_count |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for item in feature_comparisons:
        for label, baseline_count, current_count in zip(
            item.histogram_bins,
            item.baseline_histogram,
            item.current_histogram,
            strict=False,
        ):
            lines.append(
                "| "
                f"{item.feature} | "
                f"{label} | "
                f"{baseline_count} | "
                f"{current_count} |"
            )

    lines.extend(
        [
            "",
            "## Score And Prediction Distribution",
            "",
            "| signal | baseline | current | delta |",
            "| --- | ---: | ---: | ---: |",
            (
                "| average_score | "
                f"{score_comparison.baseline_average_score:.4f} | "
                f"{score_comparison.current_average_score:.4f} | "
                f"{score_comparison.average_score_delta:.4f} |"
            ),
            (
                "| high_risk_rate | "
                f"{score_comparison.baseline_high_risk_rate:.4f} | "
                f"{score_comparison.current_high_risk_rate:.4f} | "
                f"{score_comparison.high_risk_rate_delta:.4f} |"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_issue_trace_markdown(report: IssueTraceReport) -> str:
    """Render quality issue candidates."""
    lines = [
        "# Quality Issue Trace",
        "",
        "| category | evidence | owner | audit_reference | next_action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for candidate in report.candidates:
        lines.append(
            "| "
            f"{candidate.category} | "
            f"{candidate.evidence} | "
            f"{candidate.owner} | "
            f"{candidate.audit_reference} | "
            f"{candidate.next_action} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_approval_report_markdown(decision: ApprovalDecision) -> str:
    """Render deployment decision report."""

    def format_observed(value: float | bool | str) -> str:
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, str):
            return value
        return f"{value:.4f}"

    failed_checks = ", ".join(decision.failed_checks) or "-"
    notes = "<br>".join(decision.notes)
    lines = [
        "# Deployment Decision Report",
        "",
        "## Decision Summary",
        "",
        (
            "| recommendation | approved | failed_checks | unresolved_risks | "
            "re_evaluation_condition |"
        ),
        "| --- | --- | --- | --- | --- |",
        (
            f"| {decision.recommendation or '-'} | "
            f"{decision.approved} | "
            f"{failed_checks} | "
            f"{', '.join(risk.area for risk in decision.unresolved_risks) or '-'} | "
            f"{decision.re_evaluation_condition or '-'} |"
        ),
        "",
        "| approved | failed_checks | notes |",
        "| --- | --- | --- |",
        f"| {decision.approved} | {failed_checks} | {notes} |",
        "",
    ]
    if decision.check_results:
        lines.extend(
            [
                "| check | observed | criterion | result |",
                "| --- | --- | --- | --- |",
            ]
        )
        for result in decision.check_results:
            status = "pass" if result.passed else "fail"
            lines.append(
                "| "
                f"{result.name} | "
                f"{format_observed(result.observed)} | "
                f"{result.criterion} | "
                f"{status} |"
            )
        lines.append("")
    if decision.unresolved_risks:
        lines.extend(
            [
                "## Unresolved Deployment Checks",
                "",
                "| area | status | 확인 결과 | owner | next_action |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for risk in decision.unresolved_risks:
            lines.append(
                "| "
                f"{risk.area} | "
                f"{risk.status} | "
                f"{risk.evidence} | "
                f"{risk.owner} | "
                f"{risk.next_action} |"
            )
        lines.append("")
    if decision.risk_tradeoffs:
        lines.extend(
            [
                "## Deployment Risk Tradeoff",
                "",
                (
                    "| decision | company_risk | 확인 결과 | missing_check | "
                    "owner | next_action |"
                ),
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for tradeoff in decision.risk_tradeoffs:
            lines.append(
                "| "
                f"{tradeoff.decision} | "
                f"{tradeoff.company_risk} | "
                f"{tradeoff.evidence} | "
                f"{tradeoff.missing_evidence} | "
                f"{tradeoff.owner} | "
                f"{tradeoff.next_action} |"
            )
        lines.append("")
    return "\n".join(lines)


def render_label_basis_report_markdown(
    *,
    source_path: str,
    target_column: str,
    allowed_labels: tuple[str, ...],
    label_mapping: dict[str, str],
    observed_counts: dict[str, int],
    support: LabelSupport,
) -> str:
    """Render label basis evidence for release reporting."""
    allowed = ", ".join(allowed_labels)
    mapping = ", ".join(
        f"{raw}->{normalized}" for raw, normalized in label_mapping.items()
    )
    evaluation_ready = (
        support.invalid_count == 0
        and support.missing_count == 0
        and support.positive_count > 0
        and support.negative_count > 0
    )
    lines = [
        "# Label Basis Check",
        "",
        (
            "| source | target_column | allowed_labels | label_mapping | "
            "evaluation_ready |"
        ),
        "| --- | --- | --- | --- | --- |",
        (
            f"| {source_path} | {target_column} | {allowed} | {mapping} | "
            f"{evaluation_ready} |"
        ),
        "",
        "| label | count |",
        "| --- | ---: |",
    ]
    for label, count in observed_counts.items():
        lines.append(f"| {label} | {count} |")
    lines.extend(
        [
            "",
            (
                "| positive_label | positive_count | negative_label | "
                "negative_count | invalid_count | missing_count | positive_rate |"
            ),
            "| --- | ---: | --- | ---: | ---: | ---: | ---: |",
            (
                f"| {support.positive_label} | {support.positive_count} | "
                f"{support.negative_label} | {support.negative_count} | "
                f"{support.invalid_count} | {support.missing_count} | "
                f"{support.positive_rate:.2f}% |"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown(content: str, output_path: Path) -> Path:
    """Write Markdown content to an artifact path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
