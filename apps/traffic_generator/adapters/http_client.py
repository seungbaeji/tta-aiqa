"""Requests-based Risk API client adapter."""

import time
from typing import Any

import requests
from aiqa_observability import Telemetry

from traffic_generator.domain import TrafficResponse

RISK_API_PREDICT_OPERATION = "risk-api.predict"


class RequestsPredictionClient:
    """Send one traffic payload to the public Risk API REST endpoint."""

    def __init__(
        self,
        api_url: str,
        telemetry: Telemetry,
        session: requests.Session | None = None,
    ) -> None:
        """Configure the fixed prediction URL and reusable HTTP session."""
        self._url = f"{api_url.rstrip('/')}/v1/predict"
        self._telemetry = telemetry
        self._session = session or requests.Session()

    def predict(
        self,
        *,
        features: dict[str, object],
        request_id: str,
        run_id: str,
        scenario: str,
        record_id: str,
        timeout_seconds: float,
    ) -> TrafficResponse:
        """Send one request and preserve any JSON or text response as evidence."""
        with self._telemetry.client_scope(
            RISK_API_PREDICT_OPERATION,
            request_id=request_id,
            run_id=run_id,
            scenario=scenario,
            attributes={
                "http_method": "POST",
                "record_id": record_id,
                "route": "/v1/predict",
                "target_service": "risk-api",
            },
        ):
            started = time.perf_counter()
            headers = self._telemetry.outbound_trace_headers()
            headers.update(
                {
                    "X-Request-ID": request_id,
                    "X-AIQA-Run-ID": run_id,
                    "X-AIQA-Record-ID": record_id,
                    "X-AIQA-Scenario": scenario,
                }
            )
            response = self._session.post(
                self._url,
                json={"features": features},
                headers=headers,
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
                run_id=run_id,
                scenario=scenario,
                record_id=record_id,
                status_code=response.status_code,
                elapsed_seconds=elapsed,
                body=body,
            )
