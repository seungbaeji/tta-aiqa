"""Evaluate release approval criteria."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_quality.model_quality.domain.evaluation_report import EvaluationReport
from ai_quality.observability.domain.quality_snapshot import QualitySnapshot
from ai_quality.qa_strategy.domain.approval_rule import (
    ApprovalCheckResult,
    ApprovalCriteria,
    ApprovalDecision,
    ApprovalRisk,
    ReleaseRiskTradeoff,
)


@dataclass(frozen=True)
class ReleaseContext:
    """Inputs used for release approval."""

    evaluation_report: EvaluationReport
    quality_snapshot: QualitySnapshot
    contract_passed: bool
    live_deployment_verified: bool | None = None


def approval_criteria_from_config(config: dict[str, Any]) -> ApprovalCriteria:
    """Build approval criteria from config."""
    return ApprovalCriteria(
        minimum_precision=float(config["minimum_precision"]),
        minimum_recall=float(config["minimum_recall"]),
        maximum_error_rate=float(config["maximum_error_rate"]),
        maximum_latency_average_ms=float(config["maximum_latency_average_ms"]),
    )


# docs:start evaluate_release_approval
def evaluate_release_approval(
    context: ReleaseContext,
    criteria: ApprovalCriteria,
) -> ApprovalDecision:
    """Return approval decision from model, contract, and ops signals."""
    check_results: tuple[ApprovalCheckResult, ...] = (
        ApprovalCheckResult(
            name="precision",
            observed=context.evaluation_report.metrics.precision,
            criterion=f">= {criteria.minimum_precision:.4f}",
            passed=(
                context.evaluation_report.metrics.precision
                >= criteria.minimum_precision
            ),
        ),
        ApprovalCheckResult(
            name="recall",
            observed=context.evaluation_report.metrics.recall,
            criterion=f">= {criteria.minimum_recall:.4f}",
            passed=(
                context.evaluation_report.metrics.recall
                >= criteria.minimum_recall
            ),
        ),
        ApprovalCheckResult(
            name="error_rate",
            observed=context.quality_snapshot.error_rate,
            criterion=f"<= {criteria.maximum_error_rate:.4f}",
            passed=context.quality_snapshot.error_rate <= criteria.maximum_error_rate,
        ),
        ApprovalCheckResult(
            name="latency",
            observed=context.quality_snapshot.average_latency_ms,
            criterion=f"<= {criteria.maximum_latency_average_ms:.4f} ms",
            passed=(
                context.quality_snapshot.average_latency_ms
                <= criteria.maximum_latency_average_ms
            ),
        ),
        ApprovalCheckResult(
            name="prepared_api_contract",
            observed=context.contract_passed,
            criterion="local/prepared contract check is True",
            passed=context.contract_passed,
        ),
    )
    failed_checks = [result.name for result in check_results if not result.passed]
    unresolved_risks: list[ApprovalRisk] = []
    notes: list[str] = []

    if context.live_deployment_verified is None:
        unresolved_risks.append(
            ApprovalRisk(
                area="live_deployment",
                status="unverified",
                evidence=(
                    "No live /health, /predict, Pod readiness, model_version, "
                    "or threshold check in the local course artifact."
                ),
                owner="Platform/MLOps",
                next_action=(
                    "Collect live deployment smoke-test result before using "
                    "deployment readiness as an approval basis."
                ),
            )
        )
    else:
        live_result = ApprovalCheckResult(
            name="live_deployment_check",
            observed=context.live_deployment_verified,
            criterion="is True",
            passed=context.live_deployment_verified,
        )
        check_results = (*check_results, live_result)
        if not live_result.passed:
            failed_checks.append(live_result.name)

    if failed_checks:
        notes.append("실패한 기준을 검토할 때까지 배포를 보류합니다.")
    elif unresolved_risks:
        notes.append("미검증 운영 리스크를 해소할 때까지 배포를 보류합니다.")
    else:
        notes.append("설정된 QA 기준을 만족합니다.")

    failed_text = ", ".join(failed_checks) or "none"
    unresolved_text = ", ".join(risk.area for risk in unresolved_risks) or "none"
    recommendation = (
        "conditional_hold"
        if failed_checks or unresolved_risks
        else "approve"
    )
    decision_summary = (
        f"recommendation={recommendation}; "
        f"failed_checks={failed_text}; "
        f"unresolved_risks={unresolved_text}"
    )
    risk_tradeoffs = (
        ReleaseRiskTradeoff(
            decision="approve_now",
            company_risk=(
                "기준 미달 지표와 미검증 live deployment 상태가 운영에 "
                "반영되어 FP/FN, 오류 요청, 추적 공백이 증가할 수 있습니다."
            ),
            evidence=(
                f"failed_checks={failed_text}; "
                f"unresolved_risks={unresolved_text}"
            ),
            missing_evidence=(
                "실패 기준 재측정, 검증 실패 원인 확인, live /health, "
                "/predict, Pod readiness, 응답 model_version/threshold"
            ),
            owner="QA Lead",
            next_action=(
                "승인하지 않고 owner별 확인 결과를 같은 배포 기준으로 "
                "다시 검토합니다."
            ),
        ),
        ReleaseRiskTradeoff(
            decision="conditional_hold",
            company_risk=(
                "배포 지연과 현재 운영 버전 유지 부담이 생기므로 "
                "보류 사유와 해제 조건을 명확히 공유해야 합니다."
            ),
            evidence=(
                "latency와 prepared_api_contract는 통과했지만 "
                f"{failed_text} 기준과 {unresolved_text} 리스크가 남아 있습니다."
            ),
            missing_evidence=(
                "owner별 next action 완료 결과와 같은 배포 기준 재평가"
            ),
            owner="Deployment Owner",
            next_action=(
                "Data Engineering, ML Engineering, Client Integration, "
                "Platform/MLOps 확인 결과를 모아 같은 기준으로 재평가합니다."
            ),
        ),
    )

    return ApprovalDecision(
        approved=not failed_checks and not unresolved_risks,
        failed_checks=tuple(failed_checks),
        notes=tuple(notes),
        check_results=check_results,
        unresolved_risks=tuple(unresolved_risks),
        decision_summary=decision_summary,
        recommendation=recommendation,
        risk_tradeoffs=risk_tradeoffs,
        re_evaluation_condition=(
            "failed_checks와 unresolved_risks가 해소되고 owner별 확인 결과가 "
            "같은 배포 기준을 만족하면 재평가합니다."
        ),
    )
# docs:end evaluate_release_approval
