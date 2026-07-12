"""Executed EDA Notebook contract."""

import json
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[3]
STUDENT_NOTEBOOKS = (
    Path("labs/ch01-data-quality/01_physionet_data_quality_eda.ipynb"),
    Path("labs/ch02-model-quality/01_compare_model_evidence.ipynb"),
    Path("labs/ch03-serving/01_verify_risk_api.ipynb"),
    Path("labs/ch04-observability/01_inspect_dashboard_contract.ipynb"),
    Path("labs/ch05-release-decision/01_review_release_decision.ipynb"),
)

def test_data_quality_notebook_is_executed_and_scoped_to_eda() -> None:
    path = Path("labs/ch01-data-quality/01_physionet_data_quality_eda.ipynb")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])

    assert code_cells
    assert all(cell["execution_count"] is not None for cell in code_cells)
    assert "All EDA contract checks passed." in source
    assert "Feature 선택이나 모델 튜닝은 이 실습의 범위가 아닙니다." in source


@pytest.mark.integration
@pytest.mark.parametrize("relative_path", STUDENT_NOTEBOOKS)
def test_student_notebook_executes_top_to_bottom(relative_path: Path) -> None:
    notebook = nbformat.read(ROOT / relative_path, as_version=4)

    executed = NotebookClient(
        notebook,
        timeout=300,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    ).execute()

    code_cells = [cell for cell in executed.cells if cell.cell_type == "code"]
    assert code_cells
    assert all(cell.execution_count is not None for cell in code_cells)
    assert not any(
        output.get("output_type") == "error"
        for cell in code_cells
        for output in cell.get("outputs", [])
    )
