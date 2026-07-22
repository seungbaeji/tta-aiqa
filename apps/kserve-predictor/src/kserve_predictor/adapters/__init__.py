"""KServe V2 inbound delivery adapters."""

from kserve_predictor.adapters.http import KSERVE_TRACE_EXCLUDED_URLS, build_http_app

__all__ = ["KSERVE_TRACE_EXCLUDED_URLS", "build_http_app"]
