# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repo. Read this
first — then read `.claude/rules/` for the topic-specific conventions before
making changes.

## What this project is

A Dockerized Python 3.10+ backend service that scrapes job listings, evaluates
each one against a candidate resume with an LLM, and delivers the top ranked
matches by email and CSV. Built on **Hexagonal Architecture (Ports &
Adapters)** — the core domain never imports from adapters.

- **What it does & who it's for** → `docs/prd.md`
- **How it's built (as-built architecture + diagrams)** → `docs/architecture.md`
- **Why key decisions were made (living ADR log)** → `docs/adr.md`
- **Every environment variable** → `docs/env.md`

## Commands

```bash
# Environment (first time) — deterministic, do NOT do these steps by hand
chmod +x setup.sh && ./setup.sh

# Run a search (immediate mode)
python -m src.main --query "Senior Software Engineer" --work-type remote

# Tests — run before committing
pytest tests/unit/ -v
pytest tests/unit/core/domain/ -v        # a single layer
pytest tests/unit/adapters/scrapers/test_jsearch.py -v   # a single module

# Docker
docker compose build
docker compose run agent                 # one-off run
docker compose up -d                     # scheduled mode (SCHEDULE_ENABLED=true)
```

There is **no `tests/integration/` suite** yet — only `tests/unit/`. Don't
reference or run an integration suite that doesn't exist.

## Architecture in one screen

```
Adapters → Ports ← Core Domain     (all dependencies point inward)
```

- `src/core/domain/` — Pydantic entities (`Job`, `Resume`, `MatchResult`,
  `RunReport`, `SearchProfile`, `RunCost`, `CostEstimate`, and the enums
  `ScraperName`, `WorkType`, `DatePosted`).
- `src/core/ports/` — ABC interfaces: `ScraperPort`, `EvaluatorPort`,
  `OutputPort`. Adapters subclass these; missing methods fail at instantiation.
- `src/core/services/job_search_service.py` — `JobSearchService`, the pipeline
  orchestrator (dependency-injected ports).
- `src/adapters/` — `scrapers/` (`linkedin.py` via Playwright, `jsearch.py` for
  Indeed/Glassdoor/ZipRecruiter, built by `scraper_factory.py`), `evaluator/`
  (`openai_evaluator.py`, `anthropic_evaluator.py`, `factory.py`, `prompts.py`),
  `output/` (`email_output.py`, `file_output.py`).
- Entrypoint chain: `src/main.py` (thin) → `cli/` (argparse + overrides) →
  `bootstrap.py` (load profiles) → `runner.py` / `scheduler.py` →
  `service_factory.py` (builds a `JobSearchService` per `SearchProfile`).
- `src/infra/` — `logging.py`, `cost_tracker.py`, `cost_estimator.py`.

## Non-obvious gotchas

- **Indeed, Glassdoor, and ZipRecruiter are all one adapter** (`JSearchScraper`,
  parameterized by platform) via the JSearch API (RapidAPI). They are *not*
  scraped directly — bot detection makes that non-viable. Only LinkedIn is
  scraped directly (Playwright). When "adding a job source," follow
  `/add-job-source`.
- **`MatchResult` is richer than the PRD's summary implies** — it carries
  `seniority_level`, `years_experience_detected`, `hire_recommendation`, and a
  9-category `score_breakdown` (see `src/core/domain/match_result.py`). Any
  evaluator adapter must return the full shape.
- **Cost tracking is opt-in** via `SHOW_COST_ESTIMATE=false` (default). When
  false, all tracking is bypassed for zero overhead. `EvaluatorPort.evaluate()`
  returns `tuple[MatchResult, int, int]` — `(result, input_tokens, output_tokens)`.
- **A `RunReport` is always delivered** — every run emails + writes a CSV, even
  a zero-result run (with top-5 near-misses and a suggested lower threshold).
- **Token/price rates and rate limits live in `.env`** — never hardcode pricing,
  concurrency, or delays. See `docs/env.md`.
- **`src/api/`, `src/evaluator/`, `src/scraper/`, `src/tools/` are empty stubs.**
  `src/api/` is a reserved future FastAPI entrypoint; the others are leftover
  scaffolding — real code lives under `src/adapters/`. Don't add code to them
  without reason.
- **The resume is re-parsed on every run** (no cache layer today), despite what
  the PRD's goals section says — see `docs/prd.md` §12 for the full list of
  known code/spec divergences.

## Working agreements

- Every function has type hints and a docstring; PEP 8; max line length 100.
- Domain entities are Pydantic models — never plain dicts/dataclasses.
- All secrets and config come from `.env` via `python-dotenv`. Never commit
  `.env`. Document every new variable in `docs/env.md`.
- Run `pytest tests/unit/ -v` before committing. Commit format:
  `<type>: <short description>` (feat, fix, test, docs, refactor, chore).
- Deeper conventions are split by topic under `.claude/rules/`. Reusable
  workflows are `.claude/commands/` (slash commands) and `.claude/skills/`.
