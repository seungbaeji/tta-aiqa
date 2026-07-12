"""CLI entry point for model development and sealed final evaluation."""

from __future__ import annotations

import argparse

from aiqa_observability import create_telemetry, load_telemetry_policy

from model_trainer.bootstrap import (
    bootstrap_models,
    reconcile_bootstrap_evidence,
    reconcile_final,
    run_development,
    run_feature_diagnostics,
    run_final,
)
from model_trainer.settings import ModelTrainerSettings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "development",
            "diagnostics",
            "bootstrap",
            "reconcile-bootstrap",
            "final",
            "reconcile-final",
        ),
    )
    parser.add_argument("--sealed-test-token")
    args = parser.parse_args()
    settings = ModelTrainerSettings()
    telemetry = create_telemetry(
        service_name="model-trainer",
        environment=settings.environment,
        policy=load_telemetry_policy(settings.telemetry_config_path),
        otlp_endpoint=str(settings.otlp_endpoint) if settings.otlp_endpoint else None,
    )
    try:
        with telemetry.run_scope(
            f"model_trainer.{args.command}", attributes={"command": args.command}
        ):
            if args.command == "development":
                output = run_development(settings)
            elif args.command == "diagnostics":
                output = run_feature_diagnostics(settings)
            elif args.command == "bootstrap":
                output = bootstrap_models(settings)
            elif args.command == "reconcile-bootstrap":
                output = reconcile_bootstrap_evidence(settings)
            elif args.command == "final":
                if args.sealed_test_token is None:
                    parser.error("final requires --sealed-test-token")
                output = run_final(settings, args.sealed_test_token)
            else:
                output = reconcile_final(settings)
            telemetry.event(
                "model_trainer.command.completed",
                attributes={"artifact_path": str(output), "command": args.command},
            )
    finally:
        telemetry.shutdown()
    print(output)
