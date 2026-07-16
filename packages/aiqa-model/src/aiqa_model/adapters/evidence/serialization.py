"""Public conversions between model domain evidence and JSON-safe documents."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aiqa_model.adapters.evidence.documents import (
    BenchmarkEvidenceDocument,
    FeatureDiagnosticsEvidenceDocument,
)
from aiqa_model.domain import BenchmarkResult, FeatureDiagnostics


def feature_diagnostics_to_dict(result: FeatureDiagnostics) -> dict[str, object]:
    """Convert typed feature diagnostics into the reviewable JSON evidence schema."""
    return FeatureDiagnosticsEvidenceDocument.from_domain(result).model_dump(
        mode="json"
    )


def benchmark_to_dict(result: BenchmarkResult) -> dict[str, object]:
    """Convert a benchmark result into the versioned JSON evidence schema."""
    return BenchmarkEvidenceDocument.from_domain(result).model_dump(mode="json")


def benchmark_from_dict(document: Mapping[str, Any]) -> BenchmarkResult:
    """Validate versioned JSON evidence before restoring immutable domain values."""
    return BenchmarkEvidenceDocument.model_validate(document).to_domain()
