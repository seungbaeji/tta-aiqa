"""Traffic scenario use cases."""

from traffic_generator.application.collect import (
    COURSE_COLLECTION_SCENARIOS,
    build_session_run_id,
    collect_course_session,
    update_signal_availability,
)
from traffic_generator.application.generate import build_request_id, generate_traffic

__all__ = [
    "COURSE_COLLECTION_SCENARIOS",
    "build_request_id",
    "build_session_run_id",
    "collect_course_session",
    "generate_traffic",
    "update_signal_availability",
]
