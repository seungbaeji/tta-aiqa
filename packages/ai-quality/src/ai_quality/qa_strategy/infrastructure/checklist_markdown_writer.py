"""Markdown writer for final QA checklist."""

from __future__ import annotations

from pathlib import Path

from ai_quality.qa_strategy.domain.qa_checklist import QAChecklist


def render_checklist_markdown(checklist: QAChecklist) -> str:
    """Render checklist as Markdown."""
    blocking_statuses = (
        ", ".join(checklist.blocking_statuses)
        if checklist.blocking_statuses
        else "-"
    )
    lines = [
        "# AI QA 체크리스트",
        "",
        (
            "최종 판단에 필요한 확인 항목만 모읍니다. 자세한 숫자와 "
            "근거 계보는 각 `근거` 파일에서 확인합니다."
        ),
        "",
        f"- 근거 검토율: {checklist.completion_rate:.0%}",
        f"- 릴리스 준비 상태: {'ready' if checklist.release_ready else 'blocked'}",
        f"- 차단 상태: {blocking_statuses}",
        "",
        "| 영역 | 상태 | 완료 | 확인 항목 | 근거 | QA 코멘트 | 담당 | 다음 조치 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in checklist.items:
        marker = "x" if item.done else " "
        lines.append(
            "| "
            f"{item.section} | "
            f"{item.status} | "
            f"[{marker}] | "
            f"{item.text} | "
            f"{item.evidence} | "
            f"{item.qa_comment} | "
            f"{item.owner} | "
            f"{item.next_action} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_checklist_markdown(checklist: QAChecklist, output_path: Path) -> Path:
    """Write checklist Markdown artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_checklist_markdown(checklist), encoding="utf-8")
    return output_path
