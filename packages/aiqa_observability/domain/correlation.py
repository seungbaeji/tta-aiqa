"""Shared wire contract for request and run correlation identifiers."""

from __future__ import annotations

import re
from typing import TypeGuard

CORRELATION_ID_MAX_LENGTH = 64
CORRELATION_ID_PATTERN_TEXT = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
CORRELATION_ID_PATTERN = re.compile(CORRELATION_ID_PATTERN_TEXT)


def is_valid_correlation_id(value: object) -> TypeGuard[str]:
    """Return whether a value is safe for bounded HTTP and telemetry correlation."""
    return (
        isinstance(value, str)
        and len(value) <= CORRELATION_ID_MAX_LENGTH
        and CORRELATION_ID_PATTERN.fullmatch(value) is not None
    )
