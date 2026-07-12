"""JSON-safe model benchmark evidence adapter."""

from dataclasses import asdict
from typing import Any

from aiqa_model.domain import (
    BenchmarkResult,
    BinaryMetrics,
    FeatureDiagnostics,
    MetricDistribution,
    ProfileEvaluation,
)


def feature_diagnostics_to_dict(result: FeatureDiagnostics) -> dict[str, object]:
    """Convert typed feature diagnostics into the reviewable JSON schema."""
    return {
        "schema_version": result.schema_version,
        "accessed_roles": list(result.accessed_roles),
        "test_accessed": result.test_accessed,
        "feature_count": result.feature_count,
        "selection": result.selection.value,
        "features": [asdict(item) for item in result.features],
        "top_baseline_coefficients": [
            asdict(item) for item in result.top_baseline_coefficients
        ],
        "candidate_permutation_importance": [
            asdict(item) for item in result.candidate_permutation_importance
        ],
    }


def benchmark_to_dict(result: BenchmarkResult) -> dict[str, object]:
    """Convert benchmark domain values into the versioned JSON evidence schema."""
    return {
        "schema_version": 1,
        "evaluation_role": result.evaluation_role,
        "accessed_roles": list(result.accessed_roles),
        "profiles": [
            {
                "profile": item.profile,
                "threshold": item.threshold,
                "metrics": asdict(item.metrics),
                "bootstrap_recall_lower": item.bootstrap_recall_lower,
                "cross_validation": {
                    name: asdict(distribution)
                    for name, distribution in item.cross_validation
                },
            }
            for item in result.profiles
        ],
    }


def benchmark_from_dict(document: dict[str, Any]) -> BenchmarkResult:
    """Restore benchmark domain values from validated versioned evidence."""
    if document.get("schema_version") != 1:
        raise ValueError("unsupported benchmark evidence schema")
    return BenchmarkResult(
        evaluation_role=document["evaluation_role"],
        accessed_roles=tuple(document["accessed_roles"]),
        profiles=tuple(
            ProfileEvaluation(
                profile=item["profile"],
                threshold=float(item["threshold"]),
                metrics=BinaryMetrics(**item["metrics"]),
                bootstrap_recall_lower=float(item["bootstrap_recall_lower"]),
                cross_validation=tuple(
                    (name, MetricDistribution(**distribution))
                    for name, distribution in item["cross_validation"].items()
                ),
            )
            for item in document["profiles"]
        ),
    )
