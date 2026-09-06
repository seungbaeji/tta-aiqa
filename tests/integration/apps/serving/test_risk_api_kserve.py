"""Risk API KServe backend composition tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
from risk_api.bootstrap import build_application
from risk_api.settings import RiskApiSettings


def write_feature_contract(path: Path) -> None:
    """Write the small canonical feature contract required by the serving bootstrap."""
    path.write_text(
        """schema_version: 1
name: test-contract
target: target
features:
  - name: age
    dtype: float
    nullable: true
  - name: age__missing
    dtype: boolean
    nullable: false
""",
        encoding="utf-8",
    )


def write_deployed_metadata(path: Path, *, feature_contract_sha256: str) -> None:
    """Write KServe runtime metadata for a pre-approved deployed candidate model."""
    path.write_text(
        json.dumps(
            {
                "profile": "candidate-b",
                "threshold": 0.35,
                "model_sha256": "d" * 64,
                "feature_contract": {"sha256": feature_contract_sha256},
            }
        ),
        encoding="utf-8",
    )


def test_kserve_backend_exposes_metadata_identity_without_local_bundle(
    tmp_path: Path,
) -> None:
    """The public model endpoint uses validated deployment metadata on KServe mode."""
    feature_contract_path = tmp_path / "contract.yaml"
    metadata_path = tmp_path / "metadata.json"
    write_feature_contract(feature_contract_path)
    write_deployed_metadata(
        metadata_path,
        feature_contract_sha256=hashlib.sha256(
            feature_contract_path.read_bytes()
        ).hexdigest(),
    )
    settings = RiskApiSettings(
        _env_file=None,
        _secrets_dir=tmp_path,
        model_backend="kserve",
        api_config_path="configs/serving/api.yaml",
        feature_contract_path=feature_contract_path,
        telemetry_config_path="configs/observability/telemetry.yaml",
        kserve_url="http://predictor.example.test",
        kserve_model_name="mortality-risk",
        model_metadata_path=metadata_path,
    )

    with TestClient(build_application(settings)) as client:
        model = client.get("/v1/model").json()

    assert model == {
        "backend": "kserve",
        "profile": "candidate-b",
        "version": "candidate-b-dddddddddddd",
        "threshold": 0.35,
        "feature_count": 2,
        "education_only": True,
    }
