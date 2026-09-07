"""Heading and forbidden-string contract for the Candidate B release notebook."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

NOTEBOOK = Path("labs/ch03-serving/02_release_candidate_b.ipynb")
REQUIRED_HEADINGS = (
    "## 이번 질문",
    "## 먼저 예상",
    "## 실행과 관측",
    "### 1.",
    "## 해석과 판단 기록",
    "## 다음 확인",
)
FORBIDDEN_STRINGS = (
    "kubectl",
    "argocd app create",
    "render_argocd_application.py",
    "127.0.0.1:8000",
    "http://127.0.0.1",
    "port-forward",
    "ClusterIP",
    "kubernetes.default.svc",
)


def _notebook() -> dict[str, Any]:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def _cell_source(cell: dict[str, Any]) -> str:
    source = cell["source"]
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def _source(notebook: dict[str, Any]) -> str:
    return "\n".join(_cell_source(cell) for cell in notebook["cells"])


def test_candidate_b_release_notebook_uses_lecture_script_headings() -> None:
    notebook = _notebook()
    headings = [
        line
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
        for line in _cell_source(cell).splitlines()
        if line.startswith("#")
    ]
    heading_starts = [
        next(
            heading
            for heading in headings
            if heading == required or heading.startswith(f"{required} ")
        )
        for required in REQUIRED_HEADINGS
    ]
    positions = [headings.index(heading) for heading in heading_starts]

    assert headings[0].startswith("# ")
    assert positions == sorted(positions)
    assert "## 해석과 기록" not in headings
    assert "## 결과 점검" not in headings


def test_candidate_b_notebook_forbids_cluster_shortcuts_and_compose_url() -> None:
    source = _source(_notebook())

    for token in FORBIDDEN_STRINGS:
        assert token not in source
    assert "AIQA_RISK_API_URL" in source
    assert 'os.getenv("AIQA_RISK_API_URL"' in source
    assert 'os.getenv("AIQA_RISK_API_URL",' not in source
    assert "API_NOT_RUNNING" in source
    assert "target_pending" in source
    assert "candidate-b-c712a8e52344" in source
    assert "scripts/sync_student_release.py" in source
    assert "candidate-a" in source
    assert "result" in source and "BLOCKED" in source
    assert "operational_deployment_scope" in source


def test_candidate_b_release_notebook_code_cells_use_numbered_korean_tables() -> None:
    notebook = _notebook()
    code_cells = [
        cell for cell in notebook["cells"] if cell["cell_type"] == "code"
    ]

    assert code_cells
    assert all(cell.get("execution_count") is None for cell in code_cells)
    assert all(not cell.get("outputs") for cell in code_cells)
    for cell in code_cells:
        source = _cell_source(cell).strip()
        assert re.search(r"^# [1-9]\. ", source, flags=re.MULTILINE)
        last_line = source.splitlines()[-1]
        assert last_line.startswith("pd.DataFrame(") or last_line.startswith(
            "pd.Series("
        )
