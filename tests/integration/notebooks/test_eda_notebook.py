"""Executed EDA Notebook contract."""

import json
import re
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
APPENDIX_NOTEBOOKS = (
    Path("labs/appendix/01_python_basics.ipynb"),
    Path("labs/appendix/02_pandas_basics.ipynb"),
    Path("labs/appendix/03_numpy_basics.ipynb"),
    Path("labs/appendix/04_matplotlib_basics.ipynb"),
    Path("labs/appendix/05_pandas+visualization.ipynb"),
    Path("labs/appendix/06_eda_basics.ipynb"),
    Path("labs/appendix/07_feature_engineering_basics.ipynb"),
    Path("labs/appendix/08_great_expectations_basics.ipynb"),
    Path("labs/appendix/09_dvc_basics.ipynb"),
    Path("labs/appendix/10_scikit-learn_basics.ipynb"),
    Path("labs/appendix/11_mlflow_basics.ipynb"),
)
APPENDIX_API_SNIPPETS = {
    APPENDIX_NOTEBOOKS[0]: (
        "type(",
        "id(",
        ".copy()",
        "copy.deepcopy(",
        "hash(",
        "unsafe_collect.__defaults__",
        "type(protocol_values).__len__(",
        "enumerate(",
        "zip(",
        "lambda",
        "def summarize_values(",
        "except ValueError",
    ),
    APPENDIX_NOTEBOOKS[1]: (
        "pd.Series(",
        "pd.DataFrame(",
        "pd.Index(",
        ".eq(",
        ".lt(",
        ".ge(",
        ".between(",
        ".isin(",
        ".where(",
        ".mask(",
        ".clip(",
        ".fillna(",
        ".dropna(",
        "pd.to_numeric(",
        "pd.to_datetime(",
        ".str.strip()",
        ".map(",
        ".replace(",
        "pd.cut(",
        "pd.qcut(",
        "pd.get_dummies(",
        ".duplicated(",
        ".drop_duplicates(",
        ".merge(",
        "pd.concat(",
        ".melt(",
        ".pivot(",
        "pd.date_range(",
        "pd.to_timedelta(",
        "pd.period_range(",
        "pd.MultiIndex.from_product(",
        ".groupby(",
        ".agg(",
        ".transform(",
        ".filter(",
    ),
    APPENDIX_NOTEBOOKS[2]: (
        "np.array(",
        ".shape",
        ".dtype",
        ".reshape(",
        "np.newaxis",
        "axis=0",
        "keepdims=True",
        "np.broadcast_shapes(",
        "np.shares_memory(",
        "np.isfinite(",
        "pd.NA",
        ".dtypes",
        "pd.DatetimeIndex(",
        ".sub(",
        'axis="index"',
        ".where(",
        ".array",
        ".to_numpy(",
    ),
    APPENDIX_NOTEBOOKS[3]: (
        "plt.figure(",
        ".add_subplot(",
        "plt.subplots(",
        "figsize=",
        "dpi=",
        'layout="constrained"',
        "sharex=",
        "gridspec_kw=",
        ".tick_params(",
        ".savefig(",
    ),
    APPENDIX_NOTEBOOKS[4]: (
        ".plot.line(",
        ".plot.bar(",
        ".plot.hist(",
        ".plot.barh(",
        ".boxplot(",
        ".plot.hexbin(",
        "ax=",
        "returned_ax",
        "subplots=True",
        ".get_figure(",
        ".resample(",
        "pd.crosstab(",
        ".rolling(",
        "stacked=True",
        ".yaxis.set_major_formatter(",
        "right_ax",
    ),
    APPENDIX_NOTEBOOKS[5]: (
        ".describe(",
        ".duplicated(",
        ".isna().mean(",
        ".value_counts(",
        ".corrwith(",
        ".corr(",
        "train_test_split(",
        ".plot.hist(",
        ".boxplot(",
    ),
    APPENDIX_NOTEBOOKS[6]: (
        ".groupby(",
        ".agg(",
        "mutual_info_classif(",
        "cross_val_score(",
        "LogisticRegression(",
        "RandomForestClassifier(",
        ".feature_importances_",
        "permutation_importance(",
        ".coef_",
        "roc_auc_score(",
    ),
    APPENDIX_NOTEBOOKS[7]: (
        "gx.get_context(",
        ".data_sources.add_pandas(",
        ".add_dataframe_asset(",
        ".add_batch_definition_whole_dataframe(",
        "batch.validate(",
        "gxe.ExpectColumnValuesToNotBeNull(",
        "gxe.ExpectColumnValuesToBeBetween(",
        "ExpectationSuite(",
        "ValidationDefinition(",
        "Checkpoint(",
    ),
    APPENDIX_NOTEBOOKS[8]: (
        'run_dvc("init"',
        'run_dvc("add"',
        '"stage"',
        'run_dvc("repro"',
        'run_dvc("status"',
        'run_dvc("dag"',
        'run_dvc("remote", "list")',
        '"dvc.yaml"',
        '"params.yaml"',
        '"dvc.lock"',
    ),
    APPENDIX_NOTEBOOKS[9]: (
        "train_test_split(",
        "DummyClassifier(",
        "ColumnTransformer(",
        "SimpleImputer(",
        "StandardScaler(",
        "OneHotEncoder(",
        "Pipeline(",
        "LogisticRegression(",
        "predict_proba(",
        "roc_auc_score(",
        "cross_validate(",
        "GridSearchCV(",
    ),
    APPENDIX_NOTEBOOKS[10]: (
        "mlflow.set_tracking_uri(",
        "mlflow.set_experiment(",
        "mlflow.start_run(",
        "mlflow.log_params(",
        "mlflow.log_metrics(",
        "mlflow.set_tags(",
        "mlflow.log_input(",
        "mlflow.log_dict(",
        "mlflow.sklearn.log_model(",
        "mlflow.search_runs(",
        "mlflow.pyfunc.load_model(",
        "mlflow.sklearn.autolog",
    ),
}

def test_data_quality_notebook_is_executed_and_scoped_to_eda() -> None:
    path = Path("labs/ch01-data-quality/01_physionet_data_quality_eda.ipynb")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])

    assert code_cells
    assert all(cell["execution_count"] is not None for cell in code_cells)
    assert "All EDA contract checks passed." in source
    assert "Feature 선택이나 모델 튜닝은 이 실습의 범위가 아닙니다." in source


@pytest.mark.parametrize("relative_path", APPENDIX_NOTEBOOKS)
def test_appendix_notebook_is_a_scoped_api_walkthrough(relative_path: Path) -> None:
    """Keep each appendix notebook focused on one reusable EDA tool boundary."""
    notebook = nbformat.read(ROOT / relative_path, as_version=4)
    source = "\n".join("".join(cell["source"]) for cell in notebook.cells)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    setup_cell = next(
        cell
        for cell in notebook.cells
        if cell.cell_type == "markdown"
        and "".join(cell["source"]).startswith("## 2. Setup")
    )
    reference_cell = notebook.cells[-1]
    setup_source = "".join(setup_cell["source"])
    reference_source = "".join(reference_cell["source"])
    headings = [
        line
        for cell in notebook.cells
        if cell.cell_type == "markdown"
        for line in "".join(cell["source"]).splitlines()
        if line.startswith("#")
    ]
    concept_headings = [line for line in headings if line.startswith("### ")]
    detail_headings = [line for line in headings if line.startswith("#### ")]
    appendix_number = int(relative_path.name.split("_", maxsplit=1)[0])

    assert code_cells
    assert f"# Appendix {appendix_number}." in source
    assert "## 1. Goal" in source
    assert "## 2. Setup" in source
    assert "## 3. Steps" in source
    assert "### 3-1." in source
    assert "#### 3-1-1." in source
    assert "## 4. Checks" in source
    assert "## 5. Next Steps" in source
    assert reference_cell.cell_type == "markdown"
    assert reference_source.startswith("## 6. References")
    assert "https://" in reference_source
    assert "http" not in setup_source
    assert concept_headings
    assert detail_headings
    assert all(re.match(r"^### 3-\d+\. \S", heading) for heading in concept_headings)
    assert all(
        re.match(r"^#### 3-\d+-\d+\. \S", heading)
        for heading in detail_headings
    )
    assert not any(heading.startswith("#####") for heading in headings)
    for detail_heading in detail_headings:
        detail_number = detail_heading.split()[1].removesuffix(".")
        parent_number = detail_number.rsplit("-", maxsplit=1)[0]
        assert any(
            heading.startswith(f"### {parent_number}. ")
            for heading in concept_headings
        )
    assert "All appendix checks passed." in source
    assert all(snippet in source for snippet in APPENDIX_API_SNIPPETS[relative_path])


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


@pytest.mark.integration
@pytest.mark.parametrize("relative_path", APPENDIX_NOTEBOOKS)
def test_appendix_notebook_executes_top_to_bottom(relative_path: Path) -> None:
    """Execute appendix examples without requiring the course DVC dataset."""
    notebook = nbformat.read(ROOT / relative_path, as_version=4)

    executed = NotebookClient(
        notebook,
        timeout=120,
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
