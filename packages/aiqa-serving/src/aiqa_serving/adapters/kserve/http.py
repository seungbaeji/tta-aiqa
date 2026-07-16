"""KServe V2 inference protocol scoring adapter."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import httpx

from aiqa_serving.adapters.kserve.headers import request_headers
from aiqa_serving.adapters.kserve.payload import inference_payload
from aiqa_serving.adapters.kserve.response import (
    KServeInferResponseDocument,
    positive_score,
)
from aiqa_serving.domain import FeatureValue, ModelIdentity


class KServeRiskScorer:
    """Call a KServe V2 endpoint while preserving the serving port contract."""

    def __init__(
        self,
        *,
        endpoint: str,
        model_name: str,
        feature_names: tuple[str, ...],
        identity: ModelIdentity,
        client: httpx.Client | None = None,
        headers_provider: Callable[[], Mapping[str, str]] | None = None,
    ) -> None:
        self._url = f"{endpoint.rstrip('/')}/v2/models/{model_name}/infer"
        self._ready_url = f"{endpoint.rstrip('/')}/v2/models/{model_name}/ready"
        self._model_name = model_name
        self._feature_names = feature_names
        self._identity = identity
        self._client = client or httpx.Client(timeout=10.0)
        self._headers_provider = headers_provider

    @property
    def identity(self) -> ModelIdentity:
        """Return the model identity expected from the remote predictor."""
        return self._identity

    def ready(self) -> bool:
        """Return whether the remote model-specific readiness endpoint is healthy."""
        try:
            response = self._client.get(
                self._ready_url,
                headers=request_headers(self._headers_provider),
            )
            response.raise_for_status()
            return response.json().get("ready") is True
        except (httpx.HTTPError, ValueError):
            return False

    def score(self, features: tuple[tuple[str, FeatureValue], ...]) -> float:
        """Score ordered features and validate the remote model response identity."""
        if tuple(name for name, _ in features) != self._feature_names:
            raise ValueError("scoring feature order does not match KServe contract")
        response = self._client.post(
            self._url,
            headers=request_headers(self._headers_provider),
            json=inference_payload(features),
        )
        response.raise_for_status()
        document: Mapping[str, Any] = response.json()
        inference = KServeInferResponseDocument.model_validate(document)
        if inference.model_name != self._model_name:
            raise ValueError(
                "KServe response model name does not match requested model"
            )
        if inference.model_version != self._identity.version:
            raise ValueError("KServe response model version does not match deployment")
        return positive_score(document)
