"""OTLP HTTP trace endpoint normalization."""


def normalize_traces_endpoint(endpoint: str) -> str:
    """Return the OTLP HTTP traces endpoint exactly once with no trailing slash."""
    normalized = endpoint.rstrip("/")
    if normalized.endswith("/v1/traces"):
        return normalized
    return f"{normalized}/v1/traces"
