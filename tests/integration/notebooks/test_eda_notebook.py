"""Executed EDA Notebook contract."""

import json
import re
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[3]
STUDENT_NOTEBOOKS = (
    Path("labs/chapters/ch01/01_physionet_data_quality_eda.ipynb"),
    Path("labs/chapters/ch02/00_train_valid_model_walkthrough.ipynb"),
    Path("labs/chapters/ch02/00b_trace_valid_model_selection.ipynb"),
    Path("labs/chapters/ch02/01_compare_model_evidence.ipynb"),
    Path("labs/chapters/ch03/01_verify_risk_api.ipynb"),
    Path("labs/chapters/ch04/01_inspect_dashboard_contract.ipynb"),
    Path("labs/chapters/ch05/00_compare_input_distributions.ipynb"),
    Path("labs/chapters/ch05/01_review_release_decision.ipynb"),
)
LEFTOVER_NOTEBOOKS = (
    Path("labs/chapters/ch01/02_inspect_dvc_revision_practice.ipynb"),
)
CORE_AND_LEFTOVER_NOTEBOOKS = STUDENT_NOTEBOOKS + LEFTOVER_NOTEBOOKS
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
    Path("labs/appendix/11_metrics_basics.ipynb"),
    Path("labs/appendix/12_class_imbalance_basics.ipynb"),
    Path("labs/appendix/13_mlflow_basics.ipynb"),
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
        "confusion_matrix(",
        "precision_score(",
        "recall_score(",
        "f1_score(",
        "roc_auc_score(",
        "auc(",
        "average_precision_score(",
        "brier_score_loss(",
        "log_loss(",
        "classification_report(",
        'average="macro"',
        'average="weighted"',
        "top_k_accuracy_score(",
        "mean_absolute_error(",
        "root_mean_squared_error(",
        "r2_score(",
        "mean_pinball_loss(",
        "calibration_curve(",
        "bootstrap_interval(",
    ),
    APPENDIX_NOTEBOOKS[11]: (
        "make_classification(",
        "train_test_split(",
        "stratify=target",
        "DummyClassifier(",
        "compute_class_weight(",
        'class_weight="balanced"',
        "RandomOverSampler(",
        "RandomUnderSampler(",
        "SMOTE(",
        "ImbPipeline(",
        "precision_recall_curve(",
        "average_precision_score(",
        "StratifiedKFold(",
        "cross_validate(",
        "sampling_strategy=",
    ),
    APPENDIX_NOTEBOOKS[12]: (
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

def test_data_quality_notebook_is_runnable_and_scoped_to_eda() -> None:
    path = Path("labs/chapters/ch01/01_physionet_data_quality_eda.ipynb")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])

    assert code_cells
    assert all(
        cell["execution_count"] is not None
        for cell in code_cells
        if cell["outputs"]
    )
    assert "All EDA contract checks passed." in source
    assert "특성 선택이나 모델 조정은 이 실습의 범위가 아닙니다." in source
    assert "parameter_coverage" in source
    assert "same_minute_duplicates" in source
    assert "RAW_SAMPLE_SIZE" in source
    assert "sample_paths" in source
    assert "preferred_sample" in source
    assert "PhysioNetRecordRepository" not in source
    assert "profile_raw_records" not in source
    code_source = "\n".join("".join(cell["source"]) for cell in code_cells)
    assert "parse_record(" not in code_source
    assert "load_source_contract(" not in code_source
    assert "load_aggregation_plan(" not in code_source
    assert "yaml.safe_load(" in code_source
    assert "MISSING_SENTINEL" in code_source
    assert "WINDOW_MINUTES" in code_source
    assert "assert len(raw_profile) == 4000" not in source
    assert "len(raw_profile) == len(sample_paths)" in source
    assert "48시간은 한 행으로 집계할 관측 창" in source
    assert "setup_course.py --data-only" in source
    assert (
        'raw_measurements["record_id"].nunique() == source.expected_record_count'
        not in source
    )
    assert "split_target_summary" in source
    assert "이 탐색 결과는 현상을 설명하는 근거입니다." in source
    assert "히스토그램의 비시각 등가 자료" in source
    assert "distribution_summary" in source
    assert "비시각 관찰" in source
    assert (
        "data/splits-v2/split-manifest.csv" in source
    )


def test_observability_notebook_reads_panel_level_datasources() -> None:
    """Keep dashboard inspection aligned with the Grafana JSON document shape."""
    path = Path("labs/chapters/ch04/01_inspect_dashboard_contract.ipynb")
    source = "\n".join(
        "".join(cell["source"])
        for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]
    )

    assert 'panel.get("datasource", {}).get("type", "")' in source
    assert 'target.get("datasource", {}).get("type", "")' not in source
    assert "API_METRICS_UNAVAILABLE" in source
    assert "PREDICTION_SERIES_NOT_YET_OBSERVED" in source
    assert "DASHBOARD_URL_NOT_CONFIGURED" in source
    assert "dashboard_observation" in source
    assert "target_observation" not in source
    assert "접속 정보, Alloy와 대시보드는 강사 또는 환경 담당자가 준비" in source


def test_serving_notebook_checks_the_bounded_public_api_contract() -> None:
    """Keep the live exercise aligned with the safe Risk API response contract."""
    path = Path("labs/chapters/ch03/01_verify_risk_api.ipynb")
    source = "\n".join(
        "".join(cell["source"])
        for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]
    )

    assert "expected_response_fields" in source
    assert 'valid_body["education_only"] is True' in source
    assert (
        'valid_body["request_id"] == valid_response.headers["X-Request-ID"]'
        in source
    )
    assert 'invalid_detail["code"] == "MODEL_INPUT_INVALID"' in source
    assert (
        'invalid_detail["validation_category"] in validation_categories' in source
    )
    assert '"status": "API_NOT_RUNNING"' in source


def test_release_decision_notebook_keeps_model_and_operational_gates_separate() -> None:
    """Keep a missing target observation from silently changing model approval."""
    path = Path("labs/chapters/ch05/01_review_release_decision.ipynb")
    source = "\n".join(
        "".join(cell["source"])
        for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]
    )

    assert '"operational_deployment_scope": "target_pending"' in source
    assert '"current_recommendation": "target evidence collection"' in source
    assert "rollback_required" in source
    assert '"model_approval": {' in source
    assert '"candidate-b": decisions.loc["candidate-b", "decision"]' in source


def test_distribution_notebook_marks_prepared_data_as_local_evidence() -> None:
    """Prepared input data must not be mistaken for target telemetry."""
    path = Path("labs/chapters/ch05/00_compare_input_distributions.ipynb")
    source = "\n".join(
        "".join(cell["source"])
        for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]
    )

    assert '"scope": "local"' in source
    assert '"source_kind": "course_prepared_dataset"' in source


def test_valid_selection_notebook_reads_development_evidence_only() -> None:
    """Trace slide selection on valid evidence; do not train or open sealed test."""
    path = Path("labs/chapters/ch02/00b_trace_valid_model_selection.ipynb")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
    code_source = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )

    assert "configs/model-v2/profiles.yaml" in source
    assert (
        "docs/evidence/model-v2/development-benchmark.json"
        in source
    )
    assert "class_weight" in source
    assert "cv_recall_mean" in source
    assert "이 숫자는 공식 승인이 아니며" in source
    assert "datasets/test.csv" not in source
    assert "canonical-benchmark.json" not in code_source
    assert "mlflow" not in code_source.lower()
    assert "LogisticRegression" not in source
    assert ".fit(" not in code_source


def test_compare_notebook_audits_canonical_hold_and_approve() -> None:
    """Keep official compare on sealed JSON; profiles.yaml already chose candidates."""
    path = Path("labs/chapters/ch02/01_compare_model_evidence.ipynb")
    source = "\n".join(
        "".join(cell["source"])
        for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]
    )

    assert (
        "docs/evidence/model-v2/canonical-benchmark.json"
        in source
    )
    assert "class_weight" in source
    assert 'evidence["sealed_test"]["status"] == "evaluated_once"' in source
    assert "HOLD" in source
    assert "APPROVE" in source


@pytest.mark.parametrize("relative_path", CORE_AND_LEFTOVER_NOTEBOOKS)
def test_student_notebook_is_checked_in_without_stale_outputs(
    relative_path: Path,
) -> None:
    """A learner starts every core notebook from one unambiguous clean state."""
    notebook = nbformat.read(ROOT / relative_path, as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]

    assert code_cells
    assert all(cell.execution_count is None for cell in code_cells)
    assert all(not cell.outputs for cell in code_cells)


@pytest.mark.parametrize("relative_path", CORE_AND_LEFTOVER_NOTEBOOKS)
def test_student_notebook_follows_the_learning_activity_headings(
    relative_path: Path,
) -> None:
    """Expose one repeatable question-to-record path in every core activity."""
    notebook = nbformat.read(ROOT / relative_path, as_version=4)
    headings = [
        line
        for cell in notebook.cells
        if cell.cell_type == "markdown"
        for line in cell.source.splitlines()
        if line.startswith("#")
    ]
    required = (
        "## 이번 질문",
        "## 먼저 예상",
        "## 실행과 관측",
        "## 해석과 기록",
        "## 결과 점검",
        "## 다음 확인",
    )
    positions = [headings.index(heading) for heading in required]
    numbered_steps = [
        heading
        for heading in headings
        if re.match(r"^### [1-9][0-9]*\\. ", heading)
    ]

    assert headings[0].startswith("# ")
    assert positions == sorted(positions)
    assert len(numbered_steps) == len(set(numbered_steps))


def test_mlflow_appendix_restores_the_callers_tracking_uri() -> None:
    """The optional exercise must not change a shared kernel's next MLflow run."""
    notebook = nbformat.read(ROOT / APPENDIX_NOTEBOOKS[-1], as_version=4)
    source = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    )

    assert "previous_tracking_uri = mlflow.get_tracking_uri()" in source
    assert "mlflow.set_tracking_uri(previous_tracking_uri)" in source
    assert source.index("mlflow.set_tracking_uri(previous_tracking_uri)") > (
        source.index('mlflow.set_experiment("appendix-local-tracking")')
    )


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


def test_leftover_dvc_notebook_hashes_development_files_only() -> None:
    """Leftover DVC practice hashes train/valid and does not open sealed test."""
    path = Path("labs/chapters/ch01/02_inspect_dvc_revision_practice.ipynb")
    source = "\n".join(
        "".join(cell["source"])
        for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]
    )

    assert "시간이 남을 때 여는 선택 실습입니다" in source
    assert "split-revision.json" in source
    assert "docs/evidence/data-v2/split-revision.json" in source
    assert "file_digest(" in source
    assert '"uv", "run", "dvc", "status"' in source
    assert "cwd=ROOT" in source
    assert 'train_info["path"]' in source
    assert "pd.read_csv(manifest_path)" in source
    assert "datasets/test.csv" not in source
    assert "datasets/operational.csv" not in source
    assert "E-02" not in source
    assert "setup_course.py --data-only" in source


def test_chapter_guides_mark_leftover_notebooks_as_optional() -> None:
    ch01 = Path("labs/chapters/ch01/README.md").read_text(encoding="utf-8")
    ch02 = Path("labs/chapters/ch02/README.md").read_text(encoding="utf-8")

    assert "## 2. 남는 시간 실습" in ch01
    assert "### 2-1. " in ch01
    assert "02_inspect_dvc_revision_practice.ipynb" in ch01
    assert "labs/run/log_development.py" in ch01
    assert "## 2. 남는 시간 실습" not in ch02
    assert "02_log_development_mlflow_run_practice.ipynb" not in ch02
    assert "labs/run/log_development.py" in ch02
    assert "student-development-tracking" in ch02


@pytest.mark.integration
@pytest.mark.parametrize("relative_path", CORE_AND_LEFTOVER_NOTEBOOKS)
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
