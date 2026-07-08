"""Build QA strategy reports and checklist artifacts."""

from __future__ import annotations

import pandas as pd
from ai_quality.common.labels import (
    ALLOWED_LABELS,
    LABEL_MAP,
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    TARGET_COLUMN,
)
from ai_quality.common.paths import data_path
from ai_quality.data_quality.domain.quality_report import (
    LabelSupport,
    calculate_label_support,
)
from ai_quality.labs.ch05_qa_strategy import (
    baseline_events,
    current_events,
    load_current_serving_requests,
    load_serving_requests,
    load_yaml_config,
    report_path,
)
from ai_quality.model_quality.application.evaluate_classifier import (
    calculate_binary_metrics,
)
from ai_quality.model_quality.domain.evaluation_report import EvaluationReport
from ai_quality.model_quality.infrastructure.sklearn_classifier import (
    predict_positive_scores,
    train_sklearn_classifier,
)
from ai_quality.observability.application.analyze_quality_signal import (
    analyze_quality_signal,
)
from ai_quality.observability.application.build_quality_snapshot import (
    build_quality_snapshot,
)
from ai_quality.qa_strategy.application.analyze_prediction_shift import (
    compare_score_distribution,
)
from ai_quality.qa_strategy.application.build_qa_checklist import (
    build_qa_checklist,
)
from ai_quality.qa_strategy.application.detect_input_shift import (
    compare_input_distribution,
)
from ai_quality.qa_strategy.application.evaluate_release_approval import (
    ReleaseContext,
    approval_criteria_from_config,
    evaluate_release_approval,
)
from ai_quality.qa_strategy.application.trace_quality_issue import trace_quality_issue
from ai_quality.qa_strategy.domain.approval_rule import ApprovalDecision
from ai_quality.qa_strategy.domain.drift_signal import FeatureDistributionComparison
from ai_quality.qa_strategy.domain.qa_checklist import QAChecklist, QAChecklistItem
from ai_quality.qa_strategy.infrastructure.checklist_markdown_writer import (
    write_checklist_markdown,
)
from ai_quality.qa_strategy.infrastructure.report_markdown_writer import (
    render_approval_report_markdown,
    render_drift_report_markdown,
    render_issue_trace_markdown,
    render_label_basis_report_markdown,
    write_markdown,
)


def build_label_basis_report() -> tuple[LabelSupport, dict[str, int], str]:
    """Check whether release evaluation labels use the approved label basis."""
    source_path = data_path("release_regression_cases.csv")
    dataframe = pd.read_csv(source_path)
    labels = dataframe[TARGET_COLUMN].tolist()
    support = calculate_label_support(labels)
    observed_counts = {
        str(label): int(count)
        for label, count in dataframe[TARGET_COLUMN].value_counts(dropna=False).items()
    }
    report = render_label_basis_report_markdown(
        source_path="data/release_regression_cases.csv",
        target_column=TARGET_COLUMN,
        allowed_labels=tuple(sorted(ALLOWED_LABELS)),
        label_mapping=LABEL_MAP,
        observed_counts=observed_counts,
        support=support,
    )
    return support, observed_counts, report


def build_release_evaluation_report(feature_columns: list[str]) -> EvaluationReport:
    """Evaluate release regression cases with the course RandomForest model."""
    train_dataframe = pd.read_csv(data_path("vital_signs_train.csv"))
    cases = pd.read_csv(data_path("release_regression_cases.csv"))
    evaluation_cases = cases[cases["expected_contract"] == "pass"].reset_index(
        drop=True
    )
    model = train_sklearn_classifier(
        dataframe=train_dataframe,
        feature_columns=feature_columns,
        target_column=TARGET_COLUMN,
    )
    scores = predict_positive_scores(model, evaluation_cases, feature_columns)
    return calculate_binary_metrics(
        labels=evaluation_cases[TARGET_COLUMN].tolist(),
        scores=scores,
        threshold=0.5,
        dataset_name="release_regression_pass_cases",
    )


def build_release_signoff_checklist(
    *,
    decision: ApprovalDecision,
    label_support: LabelSupport,
    feature_report: list[FeatureDistributionComparison],
) -> QAChecklist:
    """Build the filled final sign-off checklist for the chapter 5 scenario."""
    failed = ", ".join(decision.failed_checks) or "-"
    unresolved = ", ".join(risk.area for risk in decision.unresolved_risks) or "-"
    shifted_summary = ", ".join(
        f"{comparison.feature} {comparison.mean_delta:+.4f}"
        for comparison in feature_report
        if comparison.shifted
    )
    shifted_summary = shifted_summary or "shifted feature 없음"
    return QAChecklist(
        items=(
            QAChecklistItem(
                section="데이터 품질",
                text="라벨 허용값과 표본 수 확인",
                done=True,
                status="pass",
                evidence="label_basis_check.md",
                qa_comment=(
                    f"invalid={label_support.invalid_count}, "
                    f"missing={label_support.missing_count}, "
                    f"{POSITIVE_LABEL}={label_support.positive_count}, "
                    f"{NEGATIVE_LABEL}={label_support.negative_count}"
                ),
                owner="QA Lead",
                next_action="release report에 label basis 유지 근거로 첨부",
            ),
            QAChecklistItem(
                section="입력 변화",
                text="입력 분포 변화 확인",
                done=True,
                status="fail",
                evidence="drift_report.md",
                qa_comment=f"{shifted_summary} shift 확인",
                owner="Data Engineering",
                next_action="데이터 수집 경로와 upstream feed 변경 여부 확인",
            ),
            QAChecklistItem(
                section="모델 품질",
                text="정밀도와 재현율 승인 기준 확인",
                done=True,
                status="fail",
                evidence="release_approval.md",
                qa_comment=f"failed_checks={failed}",
                owner="ML Engineering",
                next_action="평가 데이터와 threshold 영향 재검토",
            ),
            QAChecklistItem(
                section="서빙 품질",
                text="준비된 API 계약 증거 확인",
                done=True,
                status="pass",
                evidence="release_approval.md",
                qa_comment="prepared_api_contract=True, live evidence와 분리",
                owner="Platform/MLOps",
                next_action="live smoke evidence와 혼동하지 않도록 보고서에 한정 표현",
            ),
            QAChecklistItem(
                section="서빙 품질",
                text="live deployment evidence 확인",
                done=True,
                status="unverified",
                evidence="release_approval.md",
                qa_comment=f"unresolved_risks={unresolved}",
                owner="Platform/MLOps",
                next_action=(
                    "/health, /predict, Pod readiness, model_version, "
                    "threshold 증거 수집"
                ),
            ),
            QAChecklistItem(
                section="운영 관측",
                text="오류율과 검증 실패 확인",
                done=True,
                status="fail",
                evidence="quality_issue_trace.md",
                qa_comment="error_rate 기준 초과와 api_validation 후보 유지",
                owner="Client Integration",
                next_action=(
                    "failed_field, client_id, source_system 기준으로 "
                    "payload 변경 확인"
                ),
            ),
            QAChecklistItem(
                section="최종 판단",
                text="배포 승인 또는 보류 의견",
                done=True,
                status="hold",
                evidence="release_approval.md",
                qa_comment=(
                    f"recommendation={decision.recommendation}, "
                    f"approved={decision.approved}"
                ),
                owner="QA Lead",
                next_action="실패 기준과 미검증 리스크 해소 후 재평가",
            ),
        )
    )


def main() -> None:
    """Build drift, issue trace, approval, and checklist artifacts."""
    baseline = baseline_events()
    current = current_events()
    feature_columns = list(
        load_yaml_config("validation", "model_features.yaml")["feature_columns"]
    )

    feature_report = compare_input_distribution(
        baseline=load_serving_requests(),
        current=load_current_serving_requests(),
        feature_columns=feature_columns,
    )
    score_report = compare_score_distribution(baseline, current)
    drift_path = write_markdown(
        render_drift_report_markdown(feature_report, score_report),
        report_path("drift_report.md"),
    )

    quality_report = analyze_quality_signal(
        build_quality_snapshot(baseline),
        build_quality_snapshot(current),
    )
    issue_report = trace_quality_issue(
        feature_report,
        score_report,
        quality_report,
        current_events=current,
    )
    issue_path = write_markdown(
        render_issue_trace_markdown(issue_report),
        report_path("quality_issue_trace.md"),
    )

    label_support, _, label_report = build_label_basis_report()
    label_path = write_markdown(
        label_report,
        report_path("label_basis_check.md"),
    )

    criteria = approval_criteria_from_config(
        load_yaml_config("qa_strategy", "approval_rules.yaml")
    )
    evaluation_report = build_release_evaluation_report(feature_columns)
    decision = evaluate_release_approval(
        context=ReleaseContext(
            evaluation_report=evaluation_report,
            quality_snapshot=build_quality_snapshot(current),
            contract_passed=True,
        ),
        criteria=criteria,
    )
    approval_path = write_markdown(
        render_approval_report_markdown(decision),
        report_path("release_approval.md"),
    )

    checklist_template = build_qa_checklist(
        load_yaml_config("qa_strategy", "qa_checklist.yaml")
    )
    checklist_template_path = write_checklist_markdown(
        checklist_template,
        report_path("ai_qa_checklist_template.md"),
    )
    release_signoff = build_release_signoff_checklist(
        decision=decision,
        label_support=label_support,
        feature_report=feature_report,
    )
    signoff_path = write_checklist_markdown(
        release_signoff,
        report_path("ai_qa_checklist.md"),
    )

    print(f"drift_report={drift_path}")
    print(f"issue_trace={issue_path}")
    print(f"label_basis={label_path}")
    print(f"release_approval={approval_path}")
    print(f"qa_checklist_template={checklist_template_path}")
    print(f"qa_checklist={signoff_path}")


if __name__ == "__main__":
    main()
