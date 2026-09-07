"""Joblib model bundle loading and contract verification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import joblib
import pandas as pd

from aiqa_serving.adapters.checksum import sha256_file
from aiqa_serving.adapters.local.metadata import LocalBundleMetadataDocument
from aiqa_serving.domain import ModelIdentity


class ProbabilityModel(Protocol):
    """Loaded model capability required by the local scoring adapter."""

    def predict_proba(self, frame: pd.DataFrame) -> object:
        """Return class probabilities for one feature frame."""


@dataclass(frozen=True)
class LoadedLocalModel:
    """Verified local model object, canonical feature order, and immutable identity."""

    model: ProbabilityModel
    feature_names: tuple[str, ...]
    identity: ModelIdentity


def load_local_model(
    bundle_path: Path,
    expected_contract_sha256: str,
    *,
    expected_model_sha256: str | None = None,
) -> LoadedLocalModel:
    """Load one bundle only when its configured contract and optional digest match."""
    model_sha256 = sha256_file(bundle_path)
    if expected_model_sha256 is not None and model_sha256 != expected_model_sha256:
        raise ValueError("model bundle digest mismatch")
    bundle = joblib.load(bundle_path)
    if not isinstance(bundle, dict) or set(bundle) != {"model", "metadata"}:
        raise ValueError("local model bundle must contain model and metadata")
    metadata = LocalBundleMetadataDocument.model_validate(bundle["metadata"])
    if metadata.feature_contract.sha256 != expected_contract_sha256:
        raise ValueError("model bundle feature contract hash mismatch")
    feature_names = tuple(
        feature.name for feature in metadata.feature_contract.features
    )
    if any(not name or name != name.strip() for name in feature_names):
        raise ValueError("model bundle feature names must be non-empty trimmed strings")
    if len(feature_names) != len(set(feature_names)):
        raise ValueError("model bundle feature names must be unique")
    model = bundle["model"]
    if not hasattr(model, "predict_proba"):
        raise ValueError("model bundle does not provide predict_proba")
    return LoadedLocalModel(
        model=model,
        feature_names=feature_names,
        identity=ModelIdentity(
            profile=metadata.profile,
            version=f"{metadata.profile}-{model_sha256[:12]}",
            threshold=metadata.threshold,
        ),
    )
