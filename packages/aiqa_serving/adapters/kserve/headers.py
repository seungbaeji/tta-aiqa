"""Outbound request-header adapter for KServe HTTP calls."""

from collections.abc import Callable, Mapping


def request_headers(
    provider: Callable[[], Mapping[str, str]] | None,
) -> dict[str, str]:
    """Resolve optional outbound context headers into a mutable HTTP header mapping."""
    return dict(provider()) if provider is not None else {}
