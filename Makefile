# Job Hunter AI — Makefile
#
# Thin wrappers around the src/ entrypoints (an immediate-run search CLI),
# the FastAPI backend, the web SPA, tests, and Docker. Run `make help` for a
# categorized list. Pass arguments through the ARGS/VAR knobs documented per
# target, e.g.:
#
#   make run QUERY="Senior Software Engineer" WORK_TYPE=remote
#   make test-path P=tests/unit/adapters/scrapers/test_jsearch.py

# --- Interpreter -------------------------------------------------------------
# Prefer the project virtualenv if it exists; fall back to python3 on PATH.
VENV       := .venv
PYTHON     := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
PYTEST     := $(PYTHON) -m pytest
MAIN       := $(PYTHON) -m src.main

# --- API / web defaults ------------------------------------------------------
API_HOST   ?= 0.0.0.0
API_PORT   ?= 8000
WEB_DIR    := web

.DEFAULT_GOAL := help

# =============================================================================
# Help
# =============================================================================
.PHONY: help
help: ## Show this help
	@echo "Job Hunter AI — make targets"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Knobs: QUERY LOCATION WORK_TYPE DATE_POSTED SCRAPERS EVALUATOR_MODEL"
	@echo "       JOB_ID STATUS NOTE  RESUME VERSION  TONE PERSON STYLE_NOTES"

# =============================================================================
# Environment
# =============================================================================
.PHONY: setup
setup: ## First-time environment setup (runs setup.sh; deterministic)
	chmod +x setup.sh && ./setup.sh

.PHONY: install
install: ## Install/refresh Python dependencies from the lockfile (uv sync)
	uv sync

# =============================================================================
# Run the pipeline (src.main — immediate/search mode)
# =============================================================================
# Optional overrides (all fall back to .env / SearchProfile when unset):
#   QUERY LOCATION WORK_TYPE DATE_POSTED SCRAPERS EVALUATOR_MODEL
_RUN_ARGS = \
	$(if $(QUERY),--query "$(QUERY)") \
	$(if $(LOCATION),--location "$(LOCATION)") \
	$(if $(WORK_TYPE),--work-type $(WORK_TYPE)) \
	$(if $(DATE_POSTED),--date-posted $(DATE_POSTED)) \
	$(if $(SCRAPERS),--scrapers $(SCRAPERS)) \
	$(if $(EVALUATOR_MODEL),--evaluator-model $(EVALUATOR_MODEL))

.PHONY: run
run: ## Run a search (immediate mode). Uses .env unless QUERY/etc. are set
	$(MAIN) $(_RUN_ARGS)

.PHONY: run-remote
run-remote: ## Run a remote search (QUERY required; location defaults to US)
	$(MAIN) --query "$(QUERY)" --work-type remote $(if $(DATE_POSTED),--date-posted $(DATE_POSTED))

# =============================================================================
# Job lifecycle, master resume, and document generation
# =============================================================================
# These ops moved from the CLI to the web API (the CLI is immediate-run only).
# Use the running server: PATCH /api/jobs/{id}/status|saved, GET/POST /api/resume
# (+ activate), POST /api/jobs/{id}/generate — or the Settings/Jobs screens.

# =============================================================================
# API backend (src.api) + web SPA (web/)
# =============================================================================
.PHONY: api
api: ## Run the FastAPI backend with reload (API_HOST/API_PORT override)
	$(PYTHON) -m uvicorn src.api.main:app --reload --host $(API_HOST) --port $(API_PORT)

.PHONY: web
web: ## Run the web SPA dev server (Vite)
	cd $(WEB_DIR) && npm run dev

.PHONY: web-install
web-install: ## Install web SPA dependencies
	cd $(WEB_DIR) && npm install

.PHONY: web-build
web-build: ## Type-check and build the web SPA for production
	cd $(WEB_DIR) && npm run build

.PHONY: web-test
web-test: ## Run the web SPA tests (Jest)
	cd $(WEB_DIR) && npm test

# =============================================================================
# Tests
# =============================================================================
.PHONY: test
test: ## Run the full unit suite
	$(PYTEST) tests/unit/ -v

.PHONY: test-path
test-path: ## Run a specific test file/dir. P=tests/unit/adapters/scrapers/test_jsearch.py
	$(PYTEST) $(P) -v

# =============================================================================
# Quality (Ruff — lint + format)
# =============================================================================
.PHONY: lint
lint: ## Lint src/ and tests/ (report only, no changes)
	uv run ruff check src tests

.PHONY: lint-fix
lint-fix: ## Lint and apply safe auto-fixes
	uv run ruff check --fix src tests

.PHONY: format
format: ## Reformat src/ and tests/ (Black-compatible)
	uv run ruff format src tests

.PHONY: format-check
format-check: ## Check formatting without writing (CI-friendly)
	uv run ruff format --check src tests

# =============================================================================
# Docker
# =============================================================================
.PHONY: docker-build
docker-build: ## Build the Docker image
	docker compose build

.PHONY: docker-run
docker-run: ## One-off agent run in Docker
	docker compose run agent

.PHONY: docker-up
docker-up: ## Start scheduled mode (detached; SCHEDULE_ENABLED=true)
	docker compose up -d

.PHONY: docker-down
docker-down: ## Stop and remove Docker containers
	docker compose down

# =============================================================================
# Housekeeping
# =============================================================================
.PHONY: clean
clean: ## Remove Python caches and compiled files
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
