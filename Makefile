.PHONY: help setup smoke check-course-data prepare-data labs lab-data-quality lab-model-quality lab-serving lab-observability lab-qa-strategy compose-up compose-down clean

UV_CACHE_DIR ?= .uv-cache
UV ?= uv --cache-dir $(UV_CACHE_DIR)
COURSE_SOURCE_DATA ?= data/human_vital_signs_dataset_2024.csv
PYTHON ?= $(UV) run python
COMPOSE ?= docker compose

help:
	@echo "AI QA student repo"
	@echo ""
	@echo "Targets:"
	@echo "  setup  - install Python dependencies"
	@echo "  smoke  - check repository structure"
	@echo "  labs   - regenerate lab artifacts from local data"
	@echo "  clean  - remove generated local outputs"

setup:
	$(UV) sync --group lab --group demo --group dev

smoke:
	@test -d labs
	@test -d data
	@test -d artifacts
	@test -d configs
	@test -d packages/ai-quality
	@test -d jupyterlite/files
	@echo "student repo structure is ready"

check-course-data:
	@if [ ! -f "$(COURSE_SOURCE_DATA)" ]; then \
		echo "Missing course source dataset: $(COURSE_SOURCE_DATA)"; \
		echo "If you only need learner evidence, inspect prepared artifacts under artifacts/ or use JupyterLite."; \
		exit 2; \
	fi

prepare-data: check-course-data
	$(PYTHON) labs/prepare_data.py

labs: prepare-data lab-data-quality lab-model-quality lab-serving lab-observability lab-qa-strategy

lab-data-quality:
	$(PYTHON) labs/ch01_data_quality/build_quality_report.py

lab-model-quality:
	$(PYTHON) labs/ch02_model_quality/train_baseline.py
	$(PYTHON) labs/ch02_model_quality/evaluate_and_record.py
	$(PYTHON) labs/ch02_model_quality/build_comparison_artifacts.py

lab-serving:
	$(PYTHON) labs/ch03_serving/check_serving_contract.py

lab-observability:
	$(PYTHON) labs/ch04_observability/build_observability_artifacts.py

lab-qa-strategy:
	$(PYTHON) labs/ch05_qa_strategy/build_qa_artifacts.py

compose-up:
	$(COMPOSE) up -d

compose-down:
	$(COMPOSE) down

clean:
	rm -rf outputs .pytest_cache .ruff_cache .mypy_cache mlruns artifacts/mlruns artifacts/mlflow artifacts/mlflow.db
