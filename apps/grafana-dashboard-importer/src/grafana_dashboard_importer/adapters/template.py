"""Native JSON dashboard template loader."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from grafana_dashboard_importer.domain import DashboardTemplate


class DashboardTemplateDocument(BaseModel):
    """External Grafana JSON template accepted by the configuration adapter."""

    model_config = ConfigDict(extra="allow", frozen=True)

    uid: str = Field(min_length=1)
    title: str = Field(min_length=1)

    def to_domain(self) -> DashboardTemplate:
        """Convert the validated JSON document into an internal template value."""
        return DashboardTemplate(
            uid=self.uid,
            title=self.title,
            document=self.model_dump(mode="python"),
        )


def load_dashboard_template(path: Path) -> DashboardTemplate:
    """Load and validate one Grafana dashboard template from JSON."""
    document: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("dashboard template root must be an object")
    return DashboardTemplateDocument.model_validate(document).to_domain()
