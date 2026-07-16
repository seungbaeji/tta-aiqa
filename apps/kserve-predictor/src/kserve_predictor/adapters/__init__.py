"""KServe V2 inbound delivery adapters."""

from kserve_predictor.adapters.http import build_http_app

__all__ = ["build_http_app"]
