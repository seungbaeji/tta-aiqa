"""Trace the Risk API's outbound KServe scoring boundary."""

from aiqa_observability import Telemetry
from aiqa_serving.domain import FeatureValue, ModelIdentity
from aiqa_serving.ports import RiskScorer

KSERVE_INFER_OPERATION = "kserve.infer"


class KServeTracingScorer:
    """Add one CLIENT span while preserving the scorer port contract."""

    def __init__(
        self,
        scorer: RiskScorer,
        *,
        telemetry: Telemetry,
        model_name: str,
    ) -> None:
        """Bind a concrete KServe scorer to the Risk API telemetry facade."""
        self._scorer = scorer
        self._telemetry = telemetry
        self._model_name = model_name

    @property
    def identity(self) -> ModelIdentity:
        """Expose the delegated scorer identity through the serving port."""
        return self._scorer.identity

    def ready(self) -> bool:
        """Delegate readiness without creating trace noise for health probes."""
        return self._scorer.ready()

    def score(self, features: tuple[tuple[str, FeatureValue], ...]) -> float:
        """Call KServe under a bounded, per-inference CLIENT span."""
        with self._telemetry.client_scope(
            KSERVE_INFER_OPERATION,
            attributes={
                "http_method": "POST",
                "model_name": self._model_name,
                "target_service": "kserve-risk-predictor",
            },
        ):
            return self._scorer.score(features)
