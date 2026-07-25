# Job Hunter AI — Makefile
#
# Thin wrappers around the src/ entrypoints (search, mark, resume, generate),
# the FastAPI backend, the web SPA, tests, and Docker. Run `make help` for a
# categorized list. Pass arguments through the ARGS/VAR knobs documented per
# target, e.g.:
#
#   make run QUERY="Senior Software Engineer" WORK_TYPE=remote
#   make mark JOB_ID=42 STATUS=applied
#   make generate-cover-letter JOB_ID=42 TONE=warm
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
# Job lifecycle (src.main mark)
# =============================================================================
# Required: JOB_ID. One of STATUS / SAVE / UNSAVE. Optional: NOTE.
#   STATUS: applied started interviewing offer rejected not_interested
.PHONY: mark
mark: ## Mark a stored job. JOB_ID=<id> STATUS=<s> [NOTE=".."] [SAVE=1|UNSAVE=1]
	$(MAIN) mark --job-id $(JOB_ID) \
		$(if $(STATUS),--status $(STATUS)) \
		$(if $(NOTE),--note "$(NOTE)") \
		$(if $(SAVE),--save) \
		$(if $(UNSAVE),--unsave)

# =============================================================================
# Master resume management (src.main resume)
# =============================================================================
.PHONY: resume-upload
resume-upload: ## Parse & cache a resume as the active version. RESUME=<file.pdf>
	$(MAIN) resume upload "$(RESUME)"

.PHONY: resume-list
resume-list: ## List stored resume versions (active one marked)
	$(MAIN) resume list

.PHONY: resume-activate
resume-activate: ## Restore an earlier resume version. VERSION=<n>
	$(MAIN) resume activate $(VERSION)

# =============================================================================
# Document generation (src.main generate)
# =============================================================================
.PHONY: generate-resume
generate-resume: ## Generate a tailored resume .docx for a job. JOB_ID=<id>
	$(MAIN) generate resume $(JOB_ID)

.PHONY: generate-cover-letter
generate-cover-letter: ## Generate a cover letter. JOB_ID=<id> [TONE= PERSON= STYLE_NOTES=]
	$(MAIN) generate cover-letter $(JOB_ID) \
		$(if $(TONE),--tone $(TONE)) \
		$(if $(PERSON),--person $(PERSON)) \
		$(if $(STYLE_NOTES),--style-notes "$(STYLE_NOTES)")

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
