"""KServe V2 inference protocol scoring adapter."""

from __future__ import annotations

import json
from typing import Any

import httpx

from aiqa_serving.domain import FeatureValue, ModelIdentity


class KServeRiskScorer:
    def __init__(
        self,
        *,
        endpoint: str,
        model_name: str,
        feature_names: tuple[str, ...],
        identity: ModelIdentity,
        client: httpx.Client | None = None,
    ) -> None:
        self._url = f"{endpoint.rstrip('/')}/v2/models/{model_name}/infer"
        self._ready_url = f"{endpoint.rstrip('/')}/v2/models/{model_name}/ready"
        self._model_name = model_name
        self._feature_names = feature_names
        self._identity = identity
        self._client = client or httpx.Client(timeout=10.0)

    @property
    def identity(self) -> ModelIdentity:
        return self._identity

    def ready(self) -> bool:
        try:
            response = self._client.get(self._ready_url)
            response.raise_for_status()
            return response.json().get("ready") is True
        except (httpx.HTTPError, ValueError):
            return False

    def score(self, features: tuple[tuple[str, FeatureValue], ...]) -> float:
        if tuple(name for name, _ in features) != self._feature_names:
            raise ValueError("scoring feature order does not match KServe contract")
        response = self._client.post(
            self._url,
            json={
                "inputs": [
                    {
                        "name": "features",
                        "shape": [1],
                        "datatype": "BYTES",
                        "data": [json.dumps(dict(features), separators=(",", ":"))],
                    }
                ]
            },
        )
        response.raise_for_status()
        document = response.json()
        if document.get("model_name") != self._model_name:
            raise ValueError(
                "KServe response model name does not match requested model"
            )
        if document.get("model_version") != self._identity.version:
            raise ValueError("KServe response model version does not match deployment")
        return _positive_score(document)


def _positive_score(document: dict[str, Any]) -> float:
    outputs = document.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("KServe response does not contain outputs")
    data: Any = outputs[0].get("data")
    while isinstance(data, list) and len(data) == 1:
        data = data[0]
    if isinstance(data, list) and len(data) == 2:
        data = data[1]
    if not isinstance(data, int | float):
        raise ValueError("KServe response does not contain a positive-class score")
    score = float(data)
    if not 0 <= score <= 1:
        raise ValueError("KServe positive-class score is outside [0, 1]")
    return score
