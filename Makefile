.PHONY: help setup smoke clean

help:
	@echo "AI QA student repo"
	@echo ""
	@echo "Targets:"
	@echo "  setup  - install Python dependencies"
	@echo "  smoke  - check repository structure"
	@echo "  clean  - remove generated local outputs"

setup:
	uv sync

smoke:
	@test -d labs
	@test -d data
	@test -d artifacts
	@test -d configs
	@echo "student repo structure is ready"

clean:
	rm -rf outputs .pytest_cache .ruff_cache .mypy_cache mlruns artifacts/mlruns artifacts/mlflow
