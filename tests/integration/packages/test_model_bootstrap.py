"""Model bundle, MLflow model, and bootstrap evidence tests."""

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest
from aiqa_core.domain import FeatureDefinition, FeatureSet, FeatureType, ModelRole
from aiqa_model.adapters import (
    MlflowModelTracker,
    load_model_bundle,
    persist_model_bundle,
)
from aiqa_model.domain import (
    BinaryMetrics,
    ModelKind,
    ModelProfile,
    ProfileEvaluation,
)
from mlflow import MlflowClient
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def profile() -> ModelProfile:
    return ModelProfile(
        name="baseline",
        model_role=ModelRole.BASELINE,
        kind=ModelKind.LOGISTIC_REGRESSION,
        threshold=0.5,
        params=(("max_iter", 100),),
    )


def evaluation() -> ProfileEvaluation:
    return ProfileEvaluation(
        profile="baseline",
        threshold=0.5,
        metrics=BinaryMetrics(
            precision=0.5,
            recall=0.5,
            f1=0.5,
            roc_auc=0.75,
            pr_auc=0.6,
            true_negative=1,
            false_positive=1,
            false_negative=1,
            true_positive=1,
        ),
        bootstrap_recall_lower=0.25,
        cross_validation=(),
    )


def fitted_pipeline() -> Pipeline:
    pipeline = Pipeline([("model", LogisticRegression(max_iter=100))])
    pipeline.fit(pd.DataFrame({"value": [0.0, 0.1, 0.9, 1.0]}), [0, 0, 1, 1])
    return pipeline


def feature_set() -> FeatureSet:
    return FeatureSet(
        schema_version=1,
        name="test-v1",
        target="target",
        features=(FeatureDefinition("value", FeatureType.FLOAT, False),),
    )


def test_model_bundle_embeds_contract_metrics_and_provenance(tmp_path: Path) -> None:
    model_path, metadata_path = persist_model_bundle(
        pipeline=fitted_pipeline(),
        profile=profile(),
        evaluation=evaluation(),
        feature_set=feature_set(),
        feature_contract_sha256="contract-hash",
        provenance={
            "dvc_lock_revision": "dvc-hash",
            "train_data_hash": "a" * 64,
            "valid_data_hash": "b" * 64,
        },
        output_dir=tmp_path,
    )

    bundle = joblib.load(model_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert bundle["metadata"]["feature_contract"]["features"][0]["name"] == "value"
    assert metadata["feature_contract"]["sha256"] == "contract-hash"
    assert metadata["validation_metrics"]["pr_auc"] == pytest.approx(0.6)
    assert metadata["provenance"]["dvc_lock_revision"] == "dvc-hash"
    assert load_model_bundle(model_path, metadata_path).predict_proba(
        pd.DataFrame({"value": [0.5]})
    ).shape == (1, 2)


def test_model_bundle_rejects_external_metadata_tampering(tmp_path: Path) -> None:
    model_path, metadata_path = persist_model_bundle(
        pipeline=fitted_pipeline(),
        profile=profile(),
        evaluation=evaluation(),
        feature_set=feature_set(),
        feature_contract_sha256="contract-hash",
        provenance={},
        output_dir=tmp_path,
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["threshold"] = 0.1
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="embedded metadata"):
        load_model_bundle(model_path, metadata_path)


@pytest.mark.integration
def test_mlflow_model_tracker_records_inputs_bundle_and_model(tmp_path: Path) -> None:
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').resolve()}"
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment_name = "model-adapter-test"
    experiment_id = client.create_experiment(
        experiment_name, artifact_location=(tmp_path / "mlruns").resolve().as_uri()
    )
    train_path = tmp_path / "train.csv"
    valid_path = tmp_path / "valid.csv"
    frame = pd.DataFrame(
        {
            "record_id": [1, 2, 3, 4],
            "value": [0.0, 0.1, 0.9, 1.0],
            "target": [0, 0, 1, 1],
        }
    )
    frame.to_csv(train_path, index=False)
    frame.to_csv(valid_path, index=False)
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "metadata.json").write_text("{}\n", encoding="utf-8")

    run_id = MlflowModelTracker(tracking_uri, experiment_name).record(
        profile=profile(),
        evaluation=evaluation(),
        pipeline=fitted_pipeline(),
        bundle_dir=bundle_dir,
        train_path=train_path,
        valid_path=valid_path,
        provenance={
            "dvc_lock_revision": "dvc-hash",
            "train_data_hash": "a" * 64,
            "valid_data_hash": "b" * 64,
        },
    )

    run = client.get_run(run_id)
    assert run.info.status == "FINISHED"
    assert {item.dataset.name for item in run.inputs.dataset_inputs} == {
        "train",
        "valid",
    }
    assert {item.dataset.digest for item in run.inputs.dataset_inputs} == {
        "a" * 32,
        "b" * 32,
    }
    assert {item.path for item in client.list_artifacts(run_id)} == {"bundle"}
    logged_models = client.search_logged_models(experiment_ids=[experiment_id])
    assert len(logged_models) == 1
    assert logged_models[0].status == "READY"
    assert logged_models[0].source_run_id == run_id


def test_prepared_bootstrap_evidence_deploys_only_baseline() -> None:
    evidence = json.loads(
        Path("reference/evidence/model/model-bootstrap.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["accessed_roles"] == ["train", "valid"]
    assert evidence["initial_deployed_profile"] == "baseline"
    assert evidence["candidate_deployment_allowed"] is False
    assert set(evidence["bundles"]) == {"baseline", "candidate-a", "candidate-b"}
    assert evidence["bundles"]["baseline"]["deployed"] is True
    assert evidence["bundles"]["candidate-a"]["deployed"] is False
    assert evidence["bundles"]["candidate-b"]["deployed"] is False
    assert all(
        not Path(item["model_path"]).is_absolute()
        for item in evidence["bundles"].values()
    )
