"""Prometheus adapter validation for metric registration and label values."""

from collections.abc import Mapping

from aiqa_observability.domain import MetricKind, MetricSpec


def validate_metric_registration(
    spec: MetricSpec,
    expected_kind: MetricKind,
    registered_names: set[str],
) -> None:
    """Reject a metric kind mismatch or duplicate process-local registration."""
    if spec.kind is not expected_kind:
        raise ValueError(f"metric {spec.name} has invalid kind")
    if spec.name in registered_names:
        raise ValueError(f"metric is already registered: {spec.name}")


def validate_metric_labels(
    labels: Mapping[str, str], expected: tuple[str, ...]
) -> dict[str, str]:
    """Return labels only when they exactly match a bounded metric declaration."""
    actual = dict(labels)
    if set(actual) != set(expected):
        raise ValueError(
            "metric labels do not match declaration: "
            f"expected={sorted(expected)}, actual={sorted(actual)}"
        )
    if any(not isinstance(value, str) for value in actual.values()):
        raise ValueError("metric label values must be strings")
    return actual
