"""Baseline deployment artifact adapter for the Model Trainer process."""

import shutil
from dataclasses import dataclass

from model_trainer.adapters.json_files import JsonFileDocumentStore, sha256_file
from model_trainer.domain import ModelTrainerConfiguration


@dataclass(frozen=True)
class BaselineBundlePublisher:
    """Copy the initial baseline bundle into the configured deployed-model directory."""

    documents: JsonFileDocumentStore

    def publish(self, configuration: ModelTrainerConfiguration) -> None:
        """Publish the baseline model and metadata with its resolved content digest."""
        source = configuration.model_bundle_dir / "baseline"
        configuration.deployed_model_dir.mkdir(parents=True, exist_ok=True)
        for name in ("model.joblib", "metadata.json"):
            shutil.copy2(source / name, configuration.deployed_model_dir / name)
        self.documents.write(
            {
                "schema_version": 1,
                "profile": "baseline",
                "model_sha256": sha256_file(
                    configuration.deployed_model_dir / "model.joblib"
                ),
                "candidate_deployment_allowed": False,
            },
            configuration.deployed_model_dir / "deployment.json",
        )
