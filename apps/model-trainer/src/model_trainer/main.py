"""CLI entry point for model development and sealed final evaluation."""

from __future__ import annotations

import argparse

from pydantic import BaseModel, ConfigDict

from model_trainer.bootstrap import bootstrap
from model_trainer.settings import ModelTrainerSettings
from model_trainer.workflow import TrainerCommand, TrainerStage


class TrainerCliDto(BaseModel):
    """Validated external CLI input for one model lifecycle stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: TrainerStage
    sealed_test_token: str | None = None

    def to_command(self) -> TrainerCommand:
        """Convert CLI input into the internal workflow request."""
        return TrainerCommand(
            stage=self.stage,
            sealed_test_token=self.sealed_test_token,
        )


def parse_args() -> TrainerCliDto:
    """Parse and validate the Model Trainer command-line request."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=tuple(stage.value for stage in TrainerStage))
    parser.add_argument("--sealed-test-token")
    return TrainerCliDto.model_validate(vars(parser.parse_args()))


def main() -> None:
    """Invoke one bound trainer workflow and print its evidence path."""
    command = parse_args().to_command()
    runtime = bootstrap(ModelTrainerSettings())
    try:
        with runtime.telemetry.run_scope(
            f"model_trainer.{command.stage}",
            attributes={"command": command.stage},
        ):
            output = runtime.run(command)
            runtime.telemetry.event(
                "model_trainer.command.completed",
                attributes={
                    "artifact_path": str(output),
                    "command": command.stage,
                },
            )
    finally:
        runtime.telemetry.shutdown()
    print(output)


if __name__ == "__main__":
    main()
