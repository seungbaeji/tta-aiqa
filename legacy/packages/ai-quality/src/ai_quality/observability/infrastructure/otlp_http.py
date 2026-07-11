"""Small OTLP/HTTP JSON client used by the Grafana Cloud demo."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any


def post_otlp_json(
    *,
    endpoint: str,
    payload: dict[str, Any],
    user: str | None = None,
    token: str | None = None,
    timeout_seconds: int = 30,
) -> tuple[int, str]:
    """Post an OTLP/HTTP JSON payload and return HTTP status and body."""
    headers = {"Content-Type": "application/json"}
    if user and token:
        credentials = base64.b64encode(f"{user}:{token}".encode()).decode("ascii")
        headers["Authorization"] = f"Basic {credentials}"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return error.code, body
    except urllib.error.URLError as error:
        return 0, f"local OTLP endpoint is not reachable: {error.reason}"
