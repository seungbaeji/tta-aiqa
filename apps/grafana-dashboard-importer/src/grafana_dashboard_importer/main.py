"""CLI entry point for idempotent dashboard import."""

import argparse
import json
from dataclasses import asdict

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
    if args.check:
        settings = GrafanaDashboardSettings()
        template = load_dashboard_template(settings.dashboard_path)
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
    print(json.dumps(asdict(bootstrap()), sort_keys=True))
