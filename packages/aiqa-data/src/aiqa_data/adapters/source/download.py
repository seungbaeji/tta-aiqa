"""Network retrieval adapter for versioned public source files."""

from urllib.request import urlopen


def download_bytes(url: str) -> bytes:
    """Download one versioned source artifact as bytes."""
    with urlopen(url, timeout=60) as response:  # noqa: S310 - versioned data URL
        return response.read()
