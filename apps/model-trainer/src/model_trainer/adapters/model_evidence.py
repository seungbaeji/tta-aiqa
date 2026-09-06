"""Pydantic model-evidence codec adapter for the Model Trainer process."""

from collections.abc import Mapping
from dataclasses import dataclass

from aiqa_model.adapters import (
    benchmark_from_dict,
    benchmark_to_dict,
    feature_diagnostics_to_dict,
)
from aiqa_model.domain import BenchmarkResult, FeatureDiagnostics


@dataclass(frozen=True)
class PydanticModelEvidenceCodec:
    """Translate model domain values through the package's Pydantic evidence DTOs."""

    def benchmark_document(self, result: BenchmarkResult) -> dict[str, object]:
        """Serialize one benchmark result for a trainer JSON artifact."""
        return benchmark_to_dict(result)

    def benchmark_result(self, document: Mapping[str, object]) -> BenchmarkResult:
        """Deserialize one validated benchmark evidence object into its domain value."""
        return benchmark_from_dict(dict(document))

    def diagnostics_document(self, result: FeatureDiagnostics) -> dict[str, object]:
        """Serialize development-only feature diagnostics for trainer evidence."""
        return feature_diagnostics_to_dict(result)
