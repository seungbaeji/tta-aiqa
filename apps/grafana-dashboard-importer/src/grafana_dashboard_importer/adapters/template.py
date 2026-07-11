"""Native JSON dashboard template loader."""

import json
from pathlib import Path
from typing import Any


def load_dashboard_template(path: Path) -> dict[str, Any]:
    document: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("dashboard template root must be an object")
    return document
