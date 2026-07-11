"""Requests-based Risk API client adapter."""

import time
from typing import Any

import requests

from traffic_generator.domain import TrafficResponse


class RequestsPredictionClient:
    def __init__(self, api_url: str, session: requests.Session | None = None) -> None:
        self._url = f"{api_url.rstrip('/')}/v1/predict"
        self._session = session or requests.Session()

    def predict(
        self,
        *,
        features: dict[str, object],
        request_id: str,
        scenario: str,
        timeout_seconds: float,
    ) -> TrafficResponse:
        started = time.perf_counter()
        response = self._session.post(
            self._url,
            json={"features": features},
            headers={
                "X-Request-ID": request_id,
                "X-AIQA-Scenario": scenario,
            },
            timeout=timeout_seconds,
        )
        elapsed = time.perf_counter() - started
        try:
            body: Any = response.json()
        except requests.JSONDecodeError:
            body = {"text": response.text}
        if not isinstance(body, dict):
            body = {"response": body}
        return TrafficResponse(
            request_id=request_id,
            scenario=scenario,
            status_code=response.status_code,
            elapsed_seconds=elapsed,
            body=body,
        )
