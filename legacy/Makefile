.PHONY: help setup smoke check-course-data prepare-data labs lab-data-quality lab-model-quality lab-serving lab-observability lab-qa-strategy compose-up compose-down clean

UV_CACHE_DIR ?= .uv-cache
UV ?= uv --cache-dir $(UV_CACHE_DIR)
COURSE ?= $(UV) run python scripts/course.py
COMPOSE ?= docker compose

help:
	@echo "AI QA student repo"
	@echo ""
	@echo "Targets:"
	@echo "  setup  - install Python dependencies"
	@echo "  smoke  - check repository structure"
	@echo "  labs   - regenerate lab artifacts from local data"
	@echo "  clean-data - remove generated root data files"
	@echo "  clean  - remove generated local outputs"

setup:
	$(UV) sync --group lab --group demo --group dev

smoke:
	$(COURSE) smoke

check-course-data:
	$(COURSE) check-course-data

prepare-data: check-course-data
	$(COURSE) prepare-data

labs: prepare-data lab-data-quality lab-model-quality lab-serving lab-observability lab-qa-strategy

lab-data-quality:
	$(COURSE) lab-data-quality

lab-model-quality:
	$(COURSE) lab-model-quality

lab-serving:
	$(COURSE) lab-serving

lab-observability:
	$(COURSE) lab-observability

lab-qa-strategy:
	$(COURSE) lab-qa-strategy

compose-up:
	$(COMPOSE) up -d

compose-down:
	$(COMPOSE) down

clean:
	$(COURSE) clean

clean-data:
	$(COURSE) clean-data
