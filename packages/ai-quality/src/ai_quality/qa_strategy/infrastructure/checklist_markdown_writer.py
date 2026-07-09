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
            "이 파일은 QA 판단 근거와 확인 상태를 한곳에 모으는 "
            "체크리스트입니다. 템플릿으로 쓸 때는 빈 항목을 채우고, "
            "제출본으로 쓸 때는 근거 산출물과 담당자, 다음 조치를 "
            "함께 남깁니다."
        ),
        "",
        "| 판단 영역 | 근거 산출물 | 보고서에 남길 필드 |",
        "| --- | --- | --- |",
        (
            "| 입력 변화 | `drift_report.md` | `heart_rate`, "
            "`oxygen_saturation`, shifted feature |"
        ),
        "| 예측 변화 | `drift_report.md` | average score, `high_risk_rate` 변화 |",
        (
            "| 원인 후보 | `quality_issue_trace.md` | category, owner, "
            "audit_reference, next_action |"
        ),
        (
            "| 배포 판단 | `release_approval.md` | approved, failed_checks, "
            "failed check 관측값 |"
        ),
        "",
        "## 근거 계보",
        "",
        (
            "최종 판단은 test 평가, validation 비교, 운영 current 관측을 "
            "분리해서 읽습니다. 아래 표는 이번 체크리스트가 어떤 데이터와 "
            "산출물에 근거하는지 보여줍니다."
        ),
        "",
        "| 판단 단계 | 근거 데이터 | 근거 산출물 | 판단 경계 |",
        "| --- | --- | --- | --- |",
        (
            "| 평가 가능성 확인 | `vital_signs_evaluation_baseline.csv` | "
            "`chapter_01_quality_report.md` | 운영 입력 정상으로 확대하지 않음 |"
        ),
        (
            "| 모델 기준 평가 | `vital_signs_train.csv`, "
            "`vital_signs_test.csv` | `model_test_eval.json` | "
            "선택된 모델과 threshold의 test 평가로 한정 |"
        ),
        (
            "| 데이터 조건 변화 비교 | `vital_signs_valid_baseline.csv`, "
            "`vital_signs_valid_degraded.csv` | "
            "`validation_degradation_comparison.json` | 운영 root cause 확정으로 쓰지 않음 |"
        ),
        (
            "| 운영 current 관측 | `serving_requests_current.csv`, "
            "`operational_current_events.jsonl` | `drift_report.md`, "
            "`quality_issue_trace.md` | 입력 구성 변화와 검증 실패를 후보 근거로 표현 |"
        ),
        (
            "| 배포 판단 | `release_regression_cases.csv` | "
            "`release_approval.md`, `ai_qa_checklist.md` | "
            "조건부 보류와 재평가 조건을 확인 결과 path로 남김 |"
        ),
        "",
        f"근거 검토율: {checklist.completion_rate:.0%}",
        f"배포 준비 상태: {'ready' if checklist.release_ready else 'blocked'}",
        f"차단 상태: {blocking_statuses}",
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
