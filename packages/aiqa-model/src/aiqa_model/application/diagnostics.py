"""Development-only feature diagnostics use case."""

from aiqa_model.domain import FeatureDiagnostics, FeatureDiagnosticsRequest
from aiqa_model.ports import FeatureDiagnostician


def diagnose_features(
    *,
    request: FeatureDiagnosticsRequest,
    diagnostician: FeatureDiagnostician,
) -> FeatureDiagnostics:
    """Produce feature evidence for the requested baseline and candidate profiles."""
    return diagnostician.produce_feature_diagnostics(request)
