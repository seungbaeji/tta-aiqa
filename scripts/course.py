"""Cross-platform course command runner.

Use this script as the primary learner-facing entry point because Windows
environments do not reliably provide `make`.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COURSE_SOURCE_DATA = ROOT / "data" / "human_vital_signs_dataset_2024.csv"

GENERATED_DATA = [
    "data/drift_requests.csv",
    "data/operational_baseline_events.jsonl",
    "data/operational_current_events.jsonl",
    "data/operational_current_stream_events.jsonl",
    "data/release_regression_cases.csv",
    "data/serving_requests.csv",
    "data/serving_requests_current.csv",
    "data/serving_requests_current_stream.csv",
    "data/serving_requests_invalid.csv",
    "data/serving_requests_valid.csv",
    "data/vital_signs.csv",
    "data/vital_signs_standardized.csv",
    "data/vital_signs_evaluation_baseline.csv",
    "data/vital_signs_train.csv",
    "data/vital_signs_valid_baseline.csv",
    "data/vital_signs_valid_degraded.csv",
    "data/vital_signs_test.csv",
    "data/vital_signs_operational_holdout.csv",
]


def run_python(script: str) -> None:
    """Run a Python script with the current interpreter."""
    subprocess.run([sys.executable, script], cwd=ROOT, check=True)


def run_bash(script: str) -> None:
    """Run a Bash script from the repository root."""
    subprocess.run(["bash", script], cwd=ROOT, check=True)


def smoke() -> None:
    """Check the expected repository structure."""
    required_paths = [
        "labs",
        "data",
        "artifacts",
        "configs",
        "packages/ai-quality",
        "jupyterlite/files",
    ]
    missing = [path for path in required_paths if not (ROOT / path).exists()]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Missing required path(s): {joined}")
    print("student repo structure is ready")


def check_course_data() -> None:
    """Ensure the source CSV needed for full regeneration exists."""
    if not COURSE_SOURCE_DATA.exists():
        raise SystemExit(
            f"Missing course source dataset: {COURSE_SOURCE_DATA}\n"
            "If you only need learner evidence, inspect prepared artifacts under "
            "artifacts/ or use JupyterLite."
        )


def prepare_data() -> None:
    """Generate derived data from the source CSV."""
    check_course_data()
    run_python("labs/prepare_data.py")


def lab_data_quality() -> None:
    run_python("labs/ch01_data_quality/04_build_quality_report.py")


def lab_model_quality() -> None:
    run_python("labs/ch02_model_quality/09_train_baseline.py")
    run_python("labs/ch02_model_quality/10_evaluate_and_record.py")
    run_python("labs/ch02_model_quality/11_build_comparison_artifacts.py")


def lab_serving() -> None:
    run_python("labs/ch03_serving/04_check_serving_contract.py")
    run_bash("demos/ch03_docker_kubernetes/scripts/02_check_argocd_manifests.sh")


def lab_observability() -> None:
    run_python("labs/ch04_observability/04_build_observability_artifacts.py")


def lab_qa_strategy() -> None:
    run_python("labs/ch05_qa_strategy/04_build_qa_artifacts.py")


def labs() -> None:
    """Regenerate all lab data and artifacts."""
    prepare_data()
    lab_data_quality()
    lab_model_quality()
    lab_serving()
    lab_observability()
    lab_qa_strategy()


def remove_path(path: Path) -> None:
    """Remove a file or directory if it exists."""
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def clean() -> None:
    """Remove local runtime outputs that should not be committed."""
    for relative_path in [
        "outputs",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "mlruns",
        "artifacts/mlruns",
        "artifacts/mlflow",
        "artifacts/mlflow.db",
    ]:
        remove_path(ROOT / relative_path)


def clean_data() -> None:
    """Remove generated root data files."""
    for relative_path in GENERATED_DATA:
        remove_path(ROOT / relative_path)


COMMANDS = {
    "smoke": smoke,
    "check-course-data": check_course_data,
    "prepare-data": prepare_data,
    "labs": labs,
    "lab-data-quality": lab_data_quality,
    "lab-model-quality": lab_model_quality,
    "lab-serving": lab_serving,
    "lab-observability": lab_observability,
    "lab-qa-strategy": lab_qa_strategy,
    "clean": clean,
    "clean-data": clean_data,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI QA course tasks.")
    parser.add_argument("command", choices=sorted(COMMANDS))
    args = parser.parse_args()
    COMMANDS[args.command]()


if __name__ == "__main__":
    main()
