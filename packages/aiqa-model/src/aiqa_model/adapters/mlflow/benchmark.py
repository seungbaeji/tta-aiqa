"""MLflow tracking adapter for benchmark result evidence."""

from dataclasses import asdict
from pathlib import Path

import mlflow

from aiqa_model.adapters.mlflow.contracts import PHYSIONET_2012_DATASET_NAME
from aiqa_model.adapters.mlflow.runtime import configure_tracking
from aiqa_model.domain import BenchmarkResult


class MlflowBenchmarkTracker:
    """Record one validation or sealed-test benchmark result as MLflow runs."""

    def __init__(
        self,
        tracking_uri: str,
        experiment_name: str,
        artifact_root: Path,
    ) -> None:
        """Bind the tracker to one MLflow server and experiment name."""
        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name
        self._artifact_root = artifact_root

    def record(
        self,
        result: BenchmarkResult,
        evidence_path: Path,
        provenance: dict[str, str],
    ) -> tuple[str, ...]:
        """Record profile metrics, role lineage, provenance tags, and JSON evidence."""
        configure_tracking(
            self._tracking_uri,
            self._experiment_name,
            self._artifact_root,
        )
        run_ids: list[str] = []
        for evaluation in result.profiles:
            with mlflow.start_run(
                run_name=f"{result.evaluation_role}-{evaluation.profile}"
            ) as run:
                mlflow.set_tags(
                    {
                        "aiqa.profile": evaluation.profile,
                        "aiqa.evaluation_role": result.evaluation_role,
                        "aiqa.accessed_roles": ",".join(result.accessed_roles),
                        "aiqa.dataset": PHYSIONET_2012_DATASET_NAME,
                        **{f"aiqa.{key}": value for key, value in provenance.items()},
                    }
                )
                mlflow.log_param("threshold", evaluation.threshold)
                mlflow.log_metrics(
                    {
                        **{
                            name: float(value)
                            for name, value in asdict(evaluation.metrics).items()
                        },
                        "bootstrap_recall_lower": evaluation.bootstrap_recall_lower,
                    }
                )
                mlflow.log_artifact(str(evidence_path), artifact_path="evidence")
                run_ids.append(run.info.run_id)
        return tuple(run_ids)
