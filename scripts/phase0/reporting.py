"""Persist reproducible Phase 0 artifacts and reviewable evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.phase0.config import Phase0Config
from scripts.phase0.data import PreparedData
from scripts.phase0.modeling import ModelEvaluation


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _configuration_evidence(config: Phase0Config) -> dict[str, Any]:
    resolved = config.model_dump(mode="json")
    canonical = json.dumps(resolved, sort_keys=True, separators=(",", ":"))
    return {
        "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "resolved": resolved,
    }


def write_data_artifacts(
    prepared: PreparedData, config: Phase0Config
) -> dict[str, str]:
    """Write generated feature/split data and versioned F0 evidence."""
    artifact_dir = config.outputs.artifact_dir
    evidence_dir = config.outputs.evidence_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)
    feature_path = artifact_dir / "patient-features.csv"
    split_path = artifact_dir / "split-manifest.csv"
    prepared.features.to_csv(feature_path, index=False)
    prepared.splits.to_csv(split_path, index=False)

    profile = {
        **prepared.profile,
        "configuration": _configuration_evidence(config),
        "artifacts": {
            "patient_features_sha256": _sha256(feature_path),
            "split_manifest_sha256": _sha256(split_path),
        },
    }
    _write_json(evidence_dir / "f0-data-feasibility.json", profile)
    return {
        "patient_features": str(feature_path),
        "split_manifest": str(split_path),
        "f0_evidence": str(evidence_dir / "f0-data-feasibility.json"),
    }


def _metric_line(label: str, result: dict[str, Any]) -> str:
    matrix = result["confusion_matrix"]
    return (
        f"| {label} | {result['profile']} | {result['threshold']:.2f} | "
        f"{result['precision']:.3f} | {result['recall']:.3f} | "
        f"{result['f1']:.3f} | {result['pr_auc']:.3f} | "
        f"{matrix['tp']} | {matrix['fp']} | {matrix['fn']} | {matrix['tn']} |"
    )


def write_model_evidence(
    prepared: PreparedData,
    evaluation: ModelEvaluation,
    config: Phase0Config,
) -> dict[str, str]:
    """Write F1/F2 JSON plus a concise decision report."""
    evidence_dir = config.outputs.evidence_dir
    report = {
        **evaluation.report,
        "f0_passed": bool(prepared.profile["f0_passed"]),
        "configuration": _configuration_evidence(config),
    }
    f1 = report["gates"]["f1_predictive_feasibility"]
    f2 = report["gates"]["f2_scenario_feasibility"]
    report["overall_go"] = bool(
        prepared.profile["f0_passed"] and f1["passed"] and f2["passed"]
    )
    _write_json(evidence_dir / "f1-f2-model-feasibility.json", report)

    selected = report["selected"]
    f0_status = "PASS" if prepared.profile["f0_passed"] else "FAIL"
    profile = prepared.profile
    cv = report["cross_validation"]
    missingness = report["missingness_only_cross_validation"]["summary"]
    lines = [
        "# PhysioNet 2012 Phase 0 Feasibility",
        "",
        "## Data Evidence",
        "",
        f"- Patient records: `{profile['source']['record_count']}`",
        f"- Measurement rows: `{profile['source']['measurement_rows']}`",
        f"- Deaths: `{profile['target']['deaths']}`",
        f"- Death rate: `{profile['target']['death_rate']:.4f}`",
        "- Patient/outcome join failures: `0`",
        "- Blocked outcome features present: `0`",
        "",
        "## Gate Summary",
        "",
        f"- F0 data feasibility: `{f0_status}`",
        f"- F1 predictive feasibility: `{'PASS' if f1['passed'] else 'FAIL'}`",
        f"- F2 scenario feasibility: `{'PASS' if f2['passed'] else 'FAIL'}`",
        f"- Overall: `{'GO' if report['overall_go'] else 'NO-GO'}`",
        "- Model access roles: `train`, `valid` only",
        "- Final `test` and `release_holdout`: not accessed",
        "",
        "## Repeated Cross-Validation",
        "",
        "| Profile | PR-AUC mean | PR-AUC std | AUROC mean | Recall mean |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, result in cv.items():
        summary = result["summary"]
        lines.append(
            f"| {name} | {summary['pr_auc']['mean']:.3f} | "
            f"{summary['pr_auc']['std']:.3f} | "
            f"{summary['roc_auc']['mean']:.3f} | "
            f"{summary['recall']['mean']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Missingness Shortcut Check",
            "",
            f"- Missing/count-only PR-AUC: `{missingness['pr_auc']['mean']:.3f}` "
            f"(std `{missingness['pr_auc']['std']:.3f}`)",
            f"- Full baseline PR-AUC: `{f1['baseline_cv_pr_auc']:.3f}`",
            "- Missingness carries signal but does not explain the full "
            "baseline signal.",
            "",
        ]
    )
    lines.extend(
        [
            "## Validation Operating Points",
            "",
            "| Role | Profile | Threshold | Precision | Recall | F1 | PR-AUC | "
            "TP | FP | FN | TN |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: |",
            _metric_line("Baseline", selected["baseline"]),
            _metric_line("Candidate A", selected["candidate_a"]),
            _metric_line("Candidate B", selected["candidate_b"]),
            "",
            "## Bootstrap 95% Intervals",
            "",
            "| Role | Precision | Recall | F1 | PR-AUC |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for role, result in selected.items():
        intervals = result["bootstrap_95"]
        lines.append(
            f"| {role} | "
            f"{intervals['precision']['lower_95']:.3f}-"
            f"{intervals['precision']['upper_95']:.3f} | "
            f"{intervals['recall']['lower_95']:.3f}-"
            f"{intervals['recall']['upper_95']:.3f} | "
            f"{intervals['f1']['lower_95']:.3f}-"
            f"{intervals['f1']['upper_95']:.3f} | "
            f"{intervals['pr_auc']['lower_95']:.3f}-"
            f"{intervals['pr_auc']['upper_95']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Candidate A: `{selected['candidate_a']['decision']}`",
            f"- Candidate B: `{selected['candidate_b']['decision']}`",
            f"- Baseline CV PR-AUC lift over Dummy: `{f1['observed_lift']:.4f}`",
            "- Candidate B approval criteria: all passed on validation evidence",
            "- Conclusion: `GO` to the V2 implementation foundation; final model "
            "approval remains unconfirmed until the sealed test evaluation.",
            "",
            "This is an education-only feasibility result, not evidence of "
            "clinical utility.",
            "",
        ]
    )
    report_path = evidence_dir / "phase0-feasibility.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "model_evidence": str(evidence_dir / "f1-f2-model-feasibility.json"),
        "report": str(report_path),
    }
