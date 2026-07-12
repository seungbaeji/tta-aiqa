"""Trusted in-memory local sklearn scoring adapter."""

from pathlib import Path

import pandas as pd

from aiqa_serving.adapters.local.loader import load_local_model
from aiqa_serving.adapters.local.probability import positive_class_probability
from aiqa_serving.domain import FeatureValue, ModelIdentity


class LocalSklearnRiskScorer:
    """Score requests with one verified bundle loaded during process construction."""

    def __init__(self, bundle_path: Path, expected_contract_sha256: str) -> None:
        self._loaded = load_local_model(bundle_path, expected_contract_sha256)

    @property
    def identity(self) -> ModelIdentity:
        """Return the immutable identity of the model loaded at process startup."""
        return self._loaded.identity

    def ready(self) -> bool:
        """Return true because construction fails when the local bundle is unusable."""
        return True

    def score(self, features: tuple[tuple[str, FeatureValue], ...]) -> float:
        """Score one ordered feature tuple with the verified local model artifact."""
        names = tuple(name for name, _ in features)
        if names != self._loaded.feature_names:
            raise ValueError("scoring feature order does not match model bundle")
        frame = pd.DataFrame([{name: value for name, value in features}])
        return positive_class_probability(self._loaded.model.predict_proba(frame))
