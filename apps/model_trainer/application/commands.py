"""Explicit CLI command dispatch for the Model Trainer process."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from model_trainer.domain import TrainerCommand, TrainerStage


@dataclass(frozen=True)
class TrainerOperations:
    """Named lifecycle functions bound by the composition root for CLI delivery."""

    development: Callable[[], Path]
    diagnostics: Callable[[], Path]
    bootstrap: Callable[[], Path]
    reconcile_bootstrap: Callable[[], Path]
    final: Callable[[str], Path]
    reconcile_final: Callable[[], Path]


def execute_trainer_command(
    command: TrainerCommand,
    *,
    operations: TrainerOperations,
) -> Path:
    """Dispatch one validated CLI command to its explicitly bound lifecycle function."""
    if command.stage is TrainerStage.DEVELOPMENT:
        return operations.development()
    if command.stage is TrainerStage.DIAGNOSTICS:
        return operations.diagnostics()
    if command.stage is TrainerStage.BOOTSTRAP:
        return operations.bootstrap()
    if command.stage is TrainerStage.RECONCILE_BOOTSTRAP:
        return operations.reconcile_bootstrap()
    if command.stage is TrainerStage.FINAL:
        assert command.sealed_test_token is not None
        return operations.final(command.sealed_test_token)
    if command.stage is TrainerStage.RECONCILE_FINAL:
        return operations.reconcile_final()
    raise ValueError(f"unsupported model trainer stage: {command.stage}")
