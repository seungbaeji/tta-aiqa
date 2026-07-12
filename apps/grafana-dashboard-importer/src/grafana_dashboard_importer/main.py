"""CLI entry point for idempotent dashboard import."""

import argparse
import json
from dataclasses import asdict

from pydantic import BaseModel, ConfigDict, ValidationError

from grafana_dashboard_importer.bootstrap import bootstrap


class DashboardCommandDto(BaseModel):
    """Validated command-line input for the dashboard delivery adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check: bool = False


def render_settings_error(error: ValidationError) -> str:
    """Render missing Grafana settings as one actionable student-facing message."""
    missing_fields = sorted(
        str(item["loc"][0])
        for item in error.errors()
        if item["type"] == "missing" and item.get("loc")
    )
    if not missing_fields:
        return "Grafana dashboard settings are invalid; inspect .env.grafanacloud."
    return (
        "Grafana dashboard settings are incomplete. Copy "
        "`.env.grafanacloud.example` to `.env.grafanacloud` and set: "
        f"{', '.join(missing_fields)}"
    )


def main() -> None:
    """Validate CLI input, invoke the bound operation, and render its result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate settings and dashboard JSON without calling Grafana",
    )
    command = DashboardCommandDto.model_validate(vars(parser.parse_args()))
    try:
        runtime = bootstrap()
    except ValidationError as error:
        parser.error(render_settings_error(error))
    try:
        if command.check:
            with runtime.telemetry.run_scope("dashboard.validate"):
                runtime.telemetry.event(
                    "dashboard.validation.completed",
                    attributes={"dashboard_uid": runtime.template.uid},
                )
            print(
                json.dumps(
                    {
                        "status": "valid",
                        "dashboard_uid": runtime.template.uid,
                        "folder_uid": runtime.folder_uid,
                    },
                    sort_keys=True,
                )
            )
            return
        with runtime.telemetry.run_scope("dashboard.import"):
            result = runtime.run_import()
            runtime.telemetry.event(
                "dashboard.import.completed",
                attributes={"dashboard_uid": result.uid},
            )
    finally:
        runtime.telemetry.shutdown()
    print(json.dumps(asdict(result), sort_keys=True))
