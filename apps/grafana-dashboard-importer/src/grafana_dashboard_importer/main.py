"""CLI entry point for idempotent dashboard import."""

import argparse
import json
from dataclasses import asdict

from aiqa_observability import create_telemetry, load_telemetry_policy

from grafana_dashboard_importer.adapters import load_dashboard_template
from grafana_dashboard_importer.bootstrap import bootstrap
from grafana_dashboard_importer.settings import GrafanaDashboardSettings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate settings and dashboard JSON without calling Grafana",
    )
    args = parser.parse_args()
    settings = GrafanaDashboardSettings()
    telemetry = create_telemetry(
        service_name="grafana-dashboard-importer",
        environment=settings.environment,
        policy=load_telemetry_policy(settings.telemetry_config_path),
        otlp_endpoint=str(settings.otlp_endpoint) if settings.otlp_endpoint else None,
    )
    try:
        if args.check:
            with telemetry.run_scope("dashboard.validate"):
                template = load_dashboard_template(settings.dashboard_path)
                telemetry.event(
                    "dashboard.validation.completed",
                    attributes={"dashboard_uid": template.uid},
                )
            print(
                json.dumps(
                    {
                        "status": "valid",
                        "dashboard_uid": template.uid,
                        "folder_uid": settings.folder_uid,
                    },
                    sort_keys=True,
                )
            )
            return
        with telemetry.run_scope("dashboard.import"):
            result = bootstrap()
            telemetry.event(
                "dashboard.import.completed",
                attributes={"dashboard_uid": result.uid},
            )
    finally:
        telemetry.shutdown()
    print(json.dumps(asdict(result), sort_keys=True))
