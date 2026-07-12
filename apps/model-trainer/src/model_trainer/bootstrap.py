"""Composition root for the Model Trainer."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aiqa_observability import Telemetry, create_telemetry, load_telemetry_policy

from model_trainer.bundles import (
    bootstrap_models,
    reconcile_bootstrap_evidence,
)
from model_trainer.development import run_development, run_feature_diagnostics
from model_trainer.finalization import reconcile_final, run_final
from model_trainer.settings import ModelTrainerSettings
from model_trainer.workflow import TrainerCommand, TrainerStage


@dataclass(frozen=True)
class ModelTrainerRuntime:
    """Bound lifecycle operation and telemetry for the CLI delivery adapter."""

    run: Callable[[TrainerCommand], Path]
    telemetry: Telemetry


def bootstrap(settings: ModelTrainerSettings) -> ModelTrainerRuntime:
    """Assemble trainer workflows from external settings and concrete adapters."""
    configuration = settings.to_configuration()

    def run(command: TrainerCommand) -> Path:
        if command.stage is TrainerStage.DEVELOPMENT:
            return run_development(configuration)
        if command.stage is TrainerStage.DIAGNOSTICS:
            return run_feature_diagnostics(configuration)
        if command.stage is TrainerStage.BOOTSTRAP:
            return bootstrap_models(configuration)
        if command.stage is TrainerStage.RECONCILE_BOOTSTRAP:
            return reconcile_bootstrap_evidence(configuration)
        if command.stage is TrainerStage.FINAL:
            assert command.sealed_test_token is not None
            return run_final(configuration, command.sealed_test_token)
        if command.stage is TrainerStage.RECONCILE_FINAL:
            return reconcile_final(configuration)
        raise ValueError(f"unsupported model trainer stage: {command.stage}")

    return ModelTrainerRuntime(
        run=run,
        telemetry=create_telemetry(
            service_name="model-trainer",
            environment=settings.environment,
            policy=load_telemetry_policy(settings.telemetry_config_path),
            otlp_endpoint=(
                str(settings.otlp_endpoint) if settings.otlp_endpoint else None
            ),
        ),
    )
