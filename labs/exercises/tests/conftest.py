"""Load the student starter unless an explicit exercise root is already on the path."""

from __future__ import annotations

import sys
from pathlib import Path

STARTER_ROOT = Path(__file__).resolve().parents[1] / "ge_summary"


def _path_provides_interpret(entry: str) -> bool:
    if not entry:
        return False
    return (Path(entry) / "interpret.py").is_file()


if not any(_path_provides_interpret(entry) for entry in sys.path):
    sys.path.insert(0, str(STARTER_ROOT))
