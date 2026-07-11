"""Trusted local sklearn bundle scoring adapter."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from aiqa_serving.domain import FeatureValue, ModelIdentity


class LocalSklearnRiskScorer:
    def __init__(self, bundle_path: Path, expected_contract_sha256: str) -> None:
        self._bundle_path = bundle_path
        self._expected_contract_sha256 = expected_contract_sha256
        self._model: Any = None
        self._feature_names: tuple[str, ...] = ()
        self._identity: ModelIdentity | None = None
        self.reload()

    @property
    def identity(self) -> ModelIdentity:
        if self._identity is None:
            raise RuntimeError("local model bundle is not loaded")
        return self._identity

    def reload(self) -> ModelIdentity:
        bundle = joblib.load(self._bundle_path)
        if not isinstance(bundle, dict) or set(bundle) != {"model", "metadata"}:
            raise ValueError("local model bundle must contain model and metadata")
        metadata = bundle["metadata"]
        contract = metadata.get("feature_contract", {})
        if contract.get("sha256") != self._expected_contract_sha256:
            raise ValueError("model bundle feature contract hash mismatch")
        features = contract.get("features", [])
        names = tuple(item["name"] for item in features)
        if not names or len(names) != len(set(names)):
            raise ValueError("model bundle feature contract is invalid")
        model_hash = _sha256(self._bundle_path)
        self._model = bundle["model"]
        self._feature_names = names
        self._identity = ModelIdentity(
            profile=metadata["profile"],
            version=f"{metadata['profile']}-{model_hash[:12]}",
            threshold=float(metadata["threshold"]),
        )
        return self._identity

    def ready(self) -> bool:
        return self._model is not None and self._identity is not None

    def score(self, features: tuple[tuple[str, FeatureValue], ...]) -> float:
        names = tuple(name for name, _ in features)
        if names != self._feature_names:
            raise ValueError("scoring feature order does not match model bundle")
        frame = pd.DataFrame([{name: value for name, value in features}])
        probability = self._model.predict_proba(frame)[0, 1]
        return float(probability)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
