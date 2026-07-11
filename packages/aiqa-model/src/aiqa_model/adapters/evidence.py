"""JSON-safe model benchmark evidence adapter."""

from dataclasses import asdict
from typing import Any

from aiqa_model.domain import (
    BenchmarkResult,
    BinaryMetrics,
    MetricDistribution,
    ProfileEvaluation,
)


def benchmark_to_dict(result: BenchmarkResult) -> dict[str, object]:
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
