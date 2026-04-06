# Project Rules

These rules apply to all contributors — human and AI alike.
Read this file before making any changes to the project.

---

## Project Overview

This is a Dockerized Python backend service that scrapes job listings
from LinkedIn, Indeed, Glassdoor, and ZipRecruiter, evaluates them
against a candidate resume using GPT-4o and Sonnet-4.5, and delivers ranked matches
via email and CSV file output.

---

## Architecture — Hexagonal (Ports and Adapters)

- Core domain logic must never import from adapters
- All dependencies point inward — adapters depend on ports,
  ports define the domain contract
- New platforms are added as new adapters only — never modify core
- Reference docs/architecture.md for the full architecture diagram

---

## Language & Runtime

- Python 3.10+
- All code runs inside the .venv virtual environment
- Activate with: source .venv/bin/activate
- All scraper and service methods must use async/await
- Use asyncio.gather for all concurrent scraping operations

---

## Domain Entities

- All domain entities must be defined as Pydantic models
- Entities live in src/core/domain/
- Valid entities: Job, Resume, MatchResult, RunReport
- Never use plain dataclasses or dicts as domain entities
- All Pydantic models must include field type hints

---

## Port Interfaces

- All ports must be defined as Abstract Base Classes (ABC)
- Ports live in src/core/ports/
- Valid ports: ScraperPort, EvaluatorPort, OutputPort
- Every adapter must explicitly subclass its corresponding port
- Missing abstract method implementations raise errors at instantiation

---

## LLM Provider

- The EVALUATOR_PROVIDER environmennt variables must be provided to use an LLM
- Models: gpt-4o, sonnnet-4.5
- Use the openai & anthropic Python SDKs for all LLM calls
- All LLM responses must be validated as Pydantic models
- Handle API errors gracefully — return default low-score
  MatchResult on failure

Alternative evaluator:
- ClaudeEvaluator uses Anthropic claude-sonnet-4-5
- Configured via ANTHROPIC_API_KEY in .env
- Identical MatchResult output to OpenAIEvaluator
- Use when OpenAI API is unavailable or for cost comparison testing
- Select via EVALUATOR_PROVIDER=anthropic in .env

---

## Secret & Configuration Management

- All secrets and config values live in .env
- Load with python-dotenv — never hardcode values
- .env is git-ignored and must never be committed
- All new environment variables must be documented in docs/env.md
- Reference docs/env.md for the full variable list

---

## Project Structure Rules

- Domain entities → src/core/domain/
- Port interfaces → src/core/ports/
- Service orchestration → src/core/services/
- Scraper adapters → src/adapters/scrapers/ (one file per platform)
- Evaluator adapter → src/adapters/evaluator/
- Output adapters → src/adapters/output/
- Unit tests → tests/unit/ (mirrors src/ structure exactly)
- Integration tests → tests/integration/ (mirrors src/ structure exactly)
- Shared fixtures → tests/conftest.py
- Static test data → tests/fixtures/
- Resume input → docs/resume/resume.pdf
- CSV output → output/results_<timestamp>.csv
- Log files → logs/agent_<timestamp>.log

---

## Work Type Rules

- Valid work types: remote, hybrid, onsite — passed via `--work-type` CLI argument
- `--location` is optional only when `--work-type remote` is the sole work type
- When `--location` is omitted with `--work-type remote`, location defaults to "United States"
- `--location` is required for hybrid, onsite, mixed work types, and when no work type is specified
- Mixed work types (e.g. `--work-type remote hybrid`) always require explicit `--location`
- Location resolution is a `main.py` concern only — `JobSearchService.run()` always receives a
  resolved, non-null location string
- Log INFO when location is defaulted: "Location not provided — defaulting to 'United States'
  for remote work type"

---

## Scraping Rules

- LinkedIn → Playwright (JavaScript-rendered, direct)
- Indeed, Glassdoor, ZipRecruiter → JSearch API (RapidAPI) — bot detection makes direct scraping non-viable for all three platforms
- Minimum 2 second delay between requests on all platforms
- Maximum 25 results per platform per run
- Always handle HTTP errors, timeouts, and empty responses
- All scraped data must be validated as Job Pydantic models

---

## Output Rules

- Results delivered via Gmail SMTP using Python smtplib
- Results saved as CSV to output/results_<timestamp>.csv
- CSV and logs are persisted via Docker volume mounts
- Score threshold is configurable via SCORE_THRESHOLD in .env
- A RunReport is always delivered — never skip email or CSV output
- Near-miss results populated only when qualifying_results is empty
- Near-miss results always capped at 5
- Near-miss results use condensed email format — no score breakdown table
- Zero results CSV filename prefixed with no_results_
- TOP_RESULTS is optional — never assume it is set
- When TOP_RESULTS is None apply no cap — return all qualifying results

---

## Code Standards

- All functions must include type hints
- All functions must include a docstring
- All tool functions must return structured JSON or Pydantic models
- Follow PEP 8 style conventions
- Maximum line length: 100 characters
- No unused imports

---

## Testing Rules

- Every module must have a unit test and an integration test
- Test files mirror src/ structure in both unit/ and integration/
- Unit tests mock all external calls — no real APIs or network
- Integration tests use saved HTML fixtures — no live network calls
- Shared fixtures defined in tests/conftest.py
- Static test data stored in tests/fixtures/
- Every test file named test_<module>.py
- Every test function named test_<function>_<scenario>()
- Run pytest tests/ -v before committing any code

---

## Docker Rules

- Single container — all-in-one
- Managed via docker-compose
- Playwright browser binaries installed inside the container
- Resume input injected via Docker volume mount
- CSV output persisted via Docker volume mount
- Log files persisted via Docker volume mount
- Secrets injected at runtime via env_file — never baked into image
- Reference ai/skills/docker.md for Docker task instructions

---

## Scraper Configuration Rules

- `ACTIVE_SCRAPERS` env variable controls which scrapers run by default
- `--scrapers` CLI argument overrides `.env` for a single run
- `ScraperName` enum defined in `src/core/domain/scraper_name.py`
- `ScraperFactory` defined in `src/adapters/scrapers/scraper_factory.py`
- Never instantiate scrapers directly in `main.py` — always use `ScraperFactory`
- Always validate scraper names at startup — exit with clear error on invalid name
- Always log active scrapers and whether source was CLI or `.env`
- At least one scraper must be active — exit with error if list is empty

---

## Scheduler Rules

- `SCHEDULE_ENABLED=true` activates APScheduler mode
- Scheduler defined in `src/scheduler.py`
- ServiceFactory defined in `src/service_factory.py`
- `SearchProfile` defined in `src/core/domain/search_profile.py`
- Each profile gets its own service instance via `build_service()`
- Profiles run sequentially not concurrently — prevents API flooding
- Profile failures are caught and logged — never stop remaining profiles
- CLI args override all profiles when provided — use for testing only
- `SCHEDULE_ENABLED` is a `.env` concern only — never a CLI argument

---

## Entrypoint Architecture

- main.py is a thin entrypoint — 30-40 lines maximum
- main.py contains no logic — only wires and dispatches
- CLI concerns live in src/cli/
- Logging config lives in src/infra/logging.py
- Profile loading lives in src/bootstrap.py
- Immediate run logic lives in src/runner.py
- bootstrap.py and runner.py have no CLI or argparse dependency — they accept plain Python objects
- src/api/ is reserved for future FastAPI implementation
- Never add logic directly to main.py

---

## Cost Tracking Rules

- `SHOW_COST_ESTIMATE` controls all cost visibility — `false` by default
- `CostTracker` lives in `src/infra/cost_tracker.py`
- `CostEstimator` lives in `src/infra/cost_estimator.py`
- `EvaluatorPort` `evaluate()` returns `tuple[MatchResult, int, int]`
  — `(result, input_tokens, output_tokens)`
- Token rates are configurable via `.env` — never hardcode pricing values in code
- Cost columns always present in CSV — empty string when tracking disabled
- Cost section in email only when `report.run_cost` is not None
- `CostTracker.enabled=False` has zero performance impact — all tracking
  bypassed entirely

---

## Rate Limiting Rules

- `MAX_CONCURRENT_EVALUATIONS` controls semaphore size — default `2`
- `EVALUATION_DELAY_SECONDS` applied after each evaluation inside semaphore — default `1.0`
- Both loaded from `.env` — never hardcoded
- Log both values at pipeline start

---

## Git Rules

- Never commit .env
- Commit message format: <type>: <short description>
- Types: feat, fix, test, docs, refactor, chore
- Example: feat: add LinkedIn scraper
- One feature or fix per commit
- Always run pytest tests/ -v before committing
