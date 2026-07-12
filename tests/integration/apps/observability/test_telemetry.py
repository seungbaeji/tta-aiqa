"""Versioned telemetry policy and Risk API metric configuration tests."""

from pathlib import Path

import pytest
from aiqa_observability import load_telemetry_policy
from pydantic import ValidationError
from risk_api.config import RiskApiObservabilityConfig, load_api_config


def test_shared_policy_contains_only_platform_concerns() -> None:
    policy = load_telemetry_policy(Path("configs/observability/telemetry.yaml"))

    assert policy.schema_version == 2
    assert policy.service_namespace == "tta-aiqa"
    assert policy.log_level == "INFO"


def test_shared_policy_rejects_app_metric_configuration(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.yaml"
    path.write_text(
        """schema_version: 2
service_namespace: tta-aiqa
logging:
  level: INFO
metrics:
  request_count: aiqa_risk_requests_total
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="metrics"):
        load_telemetry_policy(path)


def test_risk_api_owns_its_metric_names_and_bounded_dimensions() -> None:
    config = load_api_config(Path("configs/serving/api.yaml"))

    assert config.observability.metrics.request_count == "aiqa_risk_requests_total"
    assert "request_id" not in config.observability.request_metric_labels
    assert "trace_id" not in config.observability.prediction_metric_labels
    assert config.observability.fallback_scenario == "other"
    assert config.observability.fallback_method == "other"


def test_risk_api_rejects_unbounded_identifier_metric_label() -> None:
    config = load_api_config(Path("configs/serving/api.yaml")).observability
    with pytest.raises(ValidationError, match="unbounded identifier"):
        RiskApiObservabilityConfig.model_validate(
            {
                **config.model_dump(),
                "request_metric_labels": [
                    *config.request_metric_labels,
                    "request_id",
                ],
            }
        )
