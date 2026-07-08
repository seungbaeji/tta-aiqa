"""Build Chapter 2 validation degradation comparison artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from ai_quality.common.artifacts import ensure_artifact_dir
from ai_quality.common.paths import artifact_path, project_root
from ai_quality.labs.ch02_model_quality import (
    chapter_model_path,
    feature_columns,
    load_dataset,
    operating_threshold,
    target_column,
    threshold_candidates,
)
from ai_quality.model_quality.application.compare_dataset_quality import (
    compare_baseline_current_results,
)
from ai_quality.model_quality.application.evaluate_classifier import (
    calculate_binary_metrics,
    evaluate_thresholds,
)
from ai_quality.model_quality.domain.evaluation_report import EvaluationReport
from ai_quality.model_quality.domain.threshold_policy import ThresholdPolicy
from ai_quality.model_quality.infrastructure.sklearn_classifier import (
    load_model,
    predict_positive_scores,
)


def rounded(value: float | None, digits: int = 4) -> float | None:
    """Return a rounded float for stable report artifacts."""
    if value is None:
        return None
    return round(float(value), digits)


def relative_path(path: Path) -> str:
    """Return a repository-relative path when possible."""
    try:
        return path.resolve().relative_to(project_root()).as_posix()
    except ValueError:
        return str(path)


def report_to_dict(report: EvaluationReport) -> dict[str, Any]:
    """Convert an evaluation report into JSON-friendly values."""
    matrix = report.confusion_matrix
    metrics = report.metrics
    return {
        "dataset_name": report.dataset_name,
        "threshold": rounded(report.threshold, 2),
        "row_count": report.row_count,
        "confusion_matrix": {
            "true_positive": matrix.true_positive,
            "false_positive": matrix.false_positive,
            "false_negative": matrix.false_negative,
            "true_negative": matrix.true_negative,
        },
        "metrics": {
            "accuracy": rounded(metrics.accuracy),
            "precision": rounded(metrics.precision),
            "recall": rounded(metrics.recall),
            "f1_score": rounded(metrics.f1_score),
            "auroc": rounded(metrics.auroc),
            "pr_auc": rounded(metrics.pr_auc),
        },
    }


def score_summary(scores: list[float], threshold: float) -> dict[str, Any]:
    """Return score quantiles and prediction counts."""
    series = pd.Series(scores, dtype="float64")
    predictions = ThresholdPolicy(threshold=threshold).predict_many(scores)
    prediction_counts = pd.Series(predictions).value_counts().to_dict()
    return {
        "mean": rounded(float(series.mean())),
        "p10": rounded(float(series.quantile(0.10))),
        "p50": rounded(float(series.quantile(0.50))),
        "p90": rounded(float(series.quantile(0.90))),
        "prediction_counts": {
            "high_risk": int(prediction_counts.get("high_risk", 0)),
            "low_risk": int(prediction_counts.get("low_risk", 0)),
        },
    }


def evaluate_dataset(
    dataset_name: str,
    filename: str,
    model: Any,
    features: list[str],
    target: str,
    threshold: float,
) -> tuple[EvaluationReport, list[float]]:
    """Evaluate one prepared dataset with the shared baseline model."""
    dataframe = load_dataset(filename)
    scores = predict_positive_scores(model, dataframe, features)
    report = calculate_binary_metrics(
        labels=list(dataframe[target]),
        scores=scores,
        threshold=threshold,
        dataset_name=dataset_name,
    )
    return report, scores


def build_payload() -> dict[str, Any]:
    """Build the Chapter 2 comparison payload."""
    features = feature_columns()
    target = target_column()
    threshold = operating_threshold()
    model = load_model(chapter_model_path())

    valid_report, valid_scores = evaluate_dataset(
        dataset_name="valid_baseline",
        filename="vital_signs_valid_baseline.csv",
        model=model,
        features=features,
        target=target,
        threshold=threshold,
    )
    degraded_report, degraded_scores = evaluate_dataset(
        dataset_name="valid_degraded",
        filename="vital_signs_valid_degraded.csv",
        model=model,
        features=features,
        target=target,
        threshold=threshold,
    )
    test_report, test_scores = evaluate_dataset(
        dataset_name="model_test",
        filename="vital_signs_test.csv",
        model=model,
        features=features,
        target=target,
        threshold=threshold,
    )

    comparison = compare_baseline_current_results(valid_report, degraded_report)
    valid_labels = list(load_dataset("vital_signs_valid_baseline.csv")[target])
    threshold_rows = evaluate_thresholds(
        labels=valid_labels,
        scores=valid_scores,
        thresholds=threshold_candidates(),
    )

    return {
        "artifact_name": "chapter_02_validation_degradation_comparison",
        "model": {
            "model_name": "chapter_02_baseline",
            "model_version": "v1",
            "model_path": relative_path(chapter_model_path()),
            "feature_columns": features,
            "target_column": target,
            "operating_threshold": rounded(threshold, 2),
        },
        "source_artifacts": {
            "great_expectations_summary": str(
                relative_path(artifact_path(
                    "great_expectations",
                    "chapter_02_validation_summary.md",
                ))
            ),
            "model_test_eval": str(
                relative_path(artifact_path(
                    "experiments",
                    "chapter_02",
                    "model_test_eval.json",
                ))
            ),
        },
        "datasets": {
            "valid_baseline": report_to_dict(valid_report),
            "valid_degraded": report_to_dict(degraded_report),
            "model_test": report_to_dict(test_report),
        },
        "score_distribution": {
            "valid_baseline": score_summary(valid_scores, threshold),
            "valid_degraded": score_summary(degraded_scores, threshold),
            "model_test": score_summary(test_scores, threshold),
        },
        "deltas": {
            "accuracy": rounded(comparison.accuracy_delta),
            "precision": rounded(comparison.precision_delta),
            "recall": rounded(comparison.recall_delta),
            "f1_score": rounded(comparison.f1_delta),
            "false_positive": (
                degraded_report.confusion_matrix.false_positive
                - valid_report.confusion_matrix.false_positive
            ),
            "false_negative": (
                degraded_report.confusion_matrix.false_negative
                - valid_report.confusion_matrix.false_negative
            ),
            "pr_auc": rounded(
                (degraded_report.metrics.pr_auc or 0.0)
                - (valid_report.metrics.pr_auc or 0.0)
            ),
            "auroc": rounded(
                (degraded_report.metrics.auroc or 0.0)
                - (valid_report.metrics.auroc or 0.0)
            ),
        },
        "threshold_analysis": [
            {
                "threshold": rounded(row.threshold, 2),
                "precision": rounded(row.precision),
                "recall": rounded(row.recall),
                "false_positive": row.false_positive,
                "false_negative": row.false_negative,
            }
            for row in threshold_rows
        ],
        "qa_notes": list(comparison.qa_notes),
        "report_use": (
            "Prepared artifact evidence: same baseline model and threshold 0.50 "
            "compare validation baseline against validation-degraded data, then "
            "separately record the selected model and threshold on model test. "
            "Do not conclude API release approval until serving model_version, "
            "feature order, threshold, response fields, and operational holdout "
            "logs are checked in later chapters."
        ),
    }


def write_markdown_report(payload: dict[str, Any], output_path: Path) -> Path:
    """Write a report-ready Markdown artifact for Chapter 2."""
    valid = payload["datasets"]["valid_baseline"]
    degraded = payload["datasets"]["valid_degraded"]
    model_test = payload["datasets"]["model_test"]
    deltas = payload["deltas"]
    model = payload["model"]
    scores = payload["score_distribution"]

    lines = [
        "# 2장 모델 품질 비교 리포트",
        "",
        "이 리포트는 prepared artifact입니다. 직접 재생성하지 않았다면 "
        "`artifacts/reports/chapter_02_model_quality_comparison.md`에서 "
        "확인한 값이라고 보고서에 적습니다.",
        "",
        "## 비교 조건",
        "",
        "| 항목 | 값 |",
        "| --- | --- |",
        f"| model_version | `{model['model_version']}` |",
        f"| model_path | `{model['model_path']}` |",
        f"| threshold | `{model['operating_threshold']:.2f}` |",
        f"| feature_columns | `{', '.join(model['feature_columns'])}` |",
        f"| target_column | `{model['target_column']}` |",
        "",
        "## validation 기준/품질 저하 평가 데이터셋 지표 비교",
        "",
        "| 데이터셋 | Accuracy | Precision | Recall | AUROC | PR-AUC | FP | FN |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| valid_baseline | {valid['metrics']['accuracy']:.4f} | "
            f"{valid['metrics']['precision']:.4f} | "
            f"{valid['metrics']['recall']:.4f} | "
            f"{valid['metrics']['auroc']:.4f} | "
            f"{valid['metrics']['pr_auc']:.4f} | "
            f"{valid['confusion_matrix']['false_positive']} | "
            f"{valid['confusion_matrix']['false_negative']} |"
        ),
        (
            f"| valid_degraded | {degraded['metrics']['accuracy']:.4f} | "
            f"{degraded['metrics']['precision']:.4f} | "
            f"{degraded['metrics']['recall']:.4f} | "
            f"{degraded['metrics']['auroc']:.4f} | "
            f"{degraded['metrics']['pr_auc']:.4f} | "
            f"{degraded['confusion_matrix']['false_positive']} | "
            f"{degraded['confusion_matrix']['false_negative']} |"
        ),
        (
            f"| model_test | {model_test['metrics']['accuracy']:.4f} | "
            f"{model_test['metrics']['precision']:.4f} | "
            f"{model_test['metrics']['recall']:.4f} | "
            f"{model_test['metrics']['auroc']:.4f} | "
            f"{model_test['metrics']['pr_auc']:.4f} | "
            f"{model_test['confusion_matrix']['false_positive']} | "
            f"{model_test['confusion_matrix']['false_negative']} |"
        ),
        "",
        "## 변화량",
        "",
        "| 항목 | 변화량 | QA 해석 |",
        "| --- | --- | --- |",
        f"| Precision | {deltas['precision']:+.4f} | 정밀도 하락 여부 확인 |",
        f"| Recall | {deltas['recall']:+.4f} | 미탐 증가 여부 확인 |",
        (
            f"| PR-AUC | {deltas['pr_auc']:+.4f} | "
            "관심 클래스 점수 구분력 약화 후보 확인 |"
        ),
        (
            f"| FP | {deltas['false_positive']:+d} | "
            "오탐 증가로 운영 부담 증가 가능성 확인 |"
        ),
        f"| FN | {deltas['false_negative']:+d} | 미탐 변화도 함께 확인 |",
        "",
        "## 점수와 예측 분포",
        "",
        "| 데이터셋 | score mean | score p10 | score p50 | score p90 | "
        "high_risk prediction | low_risk prediction |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| valid_baseline | {scores['valid_baseline']['mean']:.4f} | "
            f"{scores['valid_baseline']['p10']:.4f} | "
            f"{scores['valid_baseline']['p50']:.4f} | "
            f"{scores['valid_baseline']['p90']:.4f} | "
            f"{scores['valid_baseline']['prediction_counts']['high_risk']} | "
            f"{scores['valid_baseline']['prediction_counts']['low_risk']} |"
        ),
        (
            f"| valid_degraded | {scores['valid_degraded']['mean']:.4f} | "
            f"{scores['valid_degraded']['p10']:.4f} | "
            f"{scores['valid_degraded']['p50']:.4f} | "
            f"{scores['valid_degraded']['p90']:.4f} | "
            f"{scores['valid_degraded']['prediction_counts']['high_risk']} | "
            f"{scores['valid_degraded']['prediction_counts']['low_risk']} |"
        ),
        "",
        "## QA 판단",
        "",
        (
            "같은 기준선 모델과 임계값 `0.50`에서 "
            "품질 저하 validation 데이터셋은 기준 validation 데이터셋보다 "
            f"Precision이 {valid['metrics']['precision']:.4f}에서 "
            f"{degraded['metrics']['precision']:.4f}로 바뀌고, "
            f"Recall은 {valid['metrics']['recall']:.4f}에서 "
            f"{degraded['metrics']['recall']:.4f}로 바뀌었습니다. FP는 "
            f"{valid['confusion_matrix']['false_positive']}건에서 "
            f"{degraded['confusion_matrix']['false_positive']}건으로, FN은 "
            f"{valid['confusion_matrix']['false_negative']}건에서 "
            f"{degraded['confusion_matrix']['false_negative']}건으로 바뀌었습니다. "
            "따라서 입력 특성 품질 저하를 모델 지표 변화의 강한 원인 후보로 남깁니다."
        ),
        "",
        "다만 이 증거만으로 모델 자체 결함이나 배포 승인/보류를 확정하지 않습니다. "
        "3장에서 API가 같은 `model_version`, feature 순서, threshold, "
        "응답 필드를 사용하는지 확인해야 합니다.",
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    """Write Chapter 2 comparison JSON and Markdown artifacts."""
    payload = build_payload()
    experiment_dir = ensure_artifact_dir("experiments", "chapter_02")
    report_dir = ensure_artifact_dir("reports")

    json_path = experiment_dir / "validation_degradation_comparison.json"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    markdown_path = write_markdown_report(
        payload=payload,
        output_path=report_dir / "chapter_02_model_quality_comparison.md",
    )

    print("comparison artifact")
    print(json_path)
    print("report artifact")
    print(markdown_path)


if __name__ == "__main__":
    main()
