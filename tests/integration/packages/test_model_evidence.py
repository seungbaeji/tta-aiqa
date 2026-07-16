"""Model evidence serialization and MLflow adapter tests."""

from pathlib import Path

import mlflow
import pytest
from aiqa_model.adapters import (
    BenchmarkResult,
    MlflowBenchmarkTracker,
    benchmark_from_dict,
    benchmark_to_dict,
    feature_diagnostics_to_dict,
)
from aiqa_model.domain import (
    BinaryMetrics,
    FeatureCoefficient,
    FeatureDiagnostics,
    FeatureSelection,
    FeatureSummary,
    PermutationImportance,
    ProfileEvaluation,
)


def benchmark_result() -> BenchmarkResult:
    return BenchmarkResult(
        evaluation_role="valid",
        accessed_roles=("train", "valid"),
        profiles=(
            ProfileEvaluation(
                profile="baseline",
                threshold=0.5,
                metrics=BinaryMetrics(
                    precision=0.4,
                    recall=0.3,
                    f1=0.34,
                    roc_auc=0.8,
                    pr_auc=0.45,
                    true_negative=80,
                    false_positive=10,
                    false_negative=7,
                    true_positive=3,
                ),
                bootstrap_recall_lower=0.2,
                cross_validation=(),
            ),
        ),
    )


def test_benchmark_evidence_round_trips_without_losing_role_boundaries() -> None:
    result = benchmark_result()

    restored = benchmark_from_dict(benchmark_to_dict(result))

    assert restored == result


def test_feature_diagnostics_serialization_preserves_role_contract() -> None:
    diagnostics = FeatureDiagnostics(
        schema_version=1,
        accessed_roles=("train", "valid"),
        test_accessed=False,
        feature_count=1,
        selection=FeatureSelection.RETAIN_ALL_CANONICAL,
        features=(FeatureSummary("age", "float", 0.1, 20, 4.0, 0.2),),
        top_baseline_coefficients=(FeatureCoefficient("age", 0.7),),
        candidate_permutation_importance=(PermutationImportance("age", 0.3, 0.1),),
    )

    document = feature_diagnostics_to_dict(diagnostics)

    assert document["selection"] == "retain_all_canonical_features"
    assert document["accessed_roles"] == ["train", "valid"]
    assert document["test_accessed"] is False
    assert document["features"][0]["feature"] == "age"


@pytest.mark.integration
def test_mlflow_tracker_records_metrics_roles_and_provenance(tmp_path: Path) -> None:
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').resolve()}"
    evidence_path = tmp_path / "benchmark.json"
    evidence_path.write_text("{}\n", encoding="utf-8")
    artifact_root = tmp_path / "mlruns"
    tracker = MlflowBenchmarkTracker(tracking_uri, "adapter-test", artifact_root)

    run_ids = tracker.record(
        benchmark_result(),
        evidence_path,
        {"dvc_lock_sha256": "abc123", "valid_dataset_sha256": "def456"},
    )

    mlflow.set_tracking_uri(tracking_uri)
    run = mlflow.get_run(run_ids[0])
    assert run.info.artifact_uri.startswith(artifact_root.resolve().as_uri())
    assert run.data.metrics["recall"] == pytest.approx(0.3)
    assert run.data.tags["aiqa.accessed_roles"] == "train,valid"
    assert run.data.tags["aiqa.dvc_lock_sha256"] == "abc123"
    assert run.data.tags["aiqa.valid_dataset_sha256"] == "def456"
