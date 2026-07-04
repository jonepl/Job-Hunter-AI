# Architecture Decision Records

## Job Search Automation Agent

A living log of significant decisions. New decisions are **appended** here (next
number, don't renumber). Each record uses the standard format: Status, Context,
Decision, Consequences. These were reverse-engineered from the code and the
former `architecture.md` §15 decision table; reasoning that wasn't visible in
code is marked inferred.

---

## ADR-001: Hexagonal Architecture (Ports & Adapters)

- **Status:** Accepted
- **Context:** The system depends on volatile external systems — job boards, LLM
  providers, email, file output — that change often and are unreliable.
- **Decision:** Organize the app as Hexagonal Architecture. Core domain logic
  never imports adapters; adapters depend on ports; all dependencies point
  inward.
- **Consequences:** Swapping a job board, LLM, or output channel needs only a new
  adapter — the core is never touched. Costs some up-front indirection (ports)
  for personal-scale code.

## ADR-002: Pydantic models for all domain entities

- **Status:** Accepted
- **Context:** Scraped HTML/API data and LLM-generated output are inherently
  unreliable and malformed data must not propagate.
- **Decision:** Define every domain entity as a Pydantic model; validate at the
  boundary.
- **Consequences:** Early, localized failures on bad data; free JSON
  serialization and type enforcement. Adds Pydantic as a hard dependency.

## ADR-003: Port interfaces as Abstract Base Classes

- **Status:** Accepted
- **Context:** Adapters must honor an explicit contract, and silent partial
  implementations are dangerous.
- **Decision:** Define ports as ABCs (`ScraperPort`, `EvaluatorPort`,
  `OutputPort`). A missing abstract method fails at instantiation.
- **Consequences:** Contract violations surface immediately, not at runtime deep
  in a run.

## ADR-004: Asynchronous scraping with asyncio

- **Status:** Accepted
- **Context:** Scraping multiple platforms sequentially is slow.
- **Decision:** Run scrapers concurrently via `asyncio.gather`; all scraper and
  service methods are `async`.
- **Consequences:** Total scrape time approaches the slowest single platform.
  Requires async discipline throughout the pipeline and `pytest-asyncio` in tests.

## ADR-005: OpenAI GPT-4o as the default evaluator

- **Status:** Accepted (see ADR-011 for the second provider)
- **Context:** Resume-to-JD evaluation needs strong reasoning and reliable
  structured output.
- **Decision:** Default to OpenAI `gpt-4o` using `response_format` strict mode.
- **Consequences:** Good structured-output reliability; incurs per-token API cost
  (mitigated by ADR-016 cost controls).

## ADR-006: Gmail SMTP for email delivery

- **Status:** Accepted
- **Context:** Results must reach the user by email without adding paid infra.
- **Decision:** Deliver via Gmail SMTP using Python's built-in `smtplib`.
- **Consequences:** Free, no third-party dependency. Requires a Gmail App
  Password; tied to Gmail's SMTP limits.

## ADR-007: CSV as the file output format

- **Status:** Accepted
- **Context:** Phase 1 needs simple, portable, human-readable persisted output.
- **Decision:** Write results to `output/results_<timestamp>.csv`.
- **Consequences:** Trivially inspectable and portable. No querying/history — a
  database is deferred to Phase 2.

## ADR-008: Single Docker container via docker-compose

- **Status:** Accepted
- **Context:** Phase 1 targets simple local execution.
- **Decision:** Ship one all-in-one container (app + Playwright + deps) managed
  by docker-compose, with resume/output/logs as volume mounts.
- **Consequences:** Simple to build and run locally. Not horizontally scalable —
  acceptable for a single-user tool.

## ADR-009: Console + file logging

- **Status:** Accepted
- **Context:** Both interactive runs and unattended scheduled runs need
  observability.
- **Decision:** Use Python `logging` with a StreamHandler (console) and
  FileHandler (`logs/agent_<timestamp>.log`, volume-mounted).
- **Consequences:** Full observability during development and scheduled runs.

## ADR-010: JSearch API for Indeed, Glassdoor, ZipRecruiter

- **Status:** Accepted (supersedes earlier per-platform direct scrapers)
- **Context:** Direct scraping of Indeed, Glassdoor, and ZipRecruiter is
  non-viable — TLS fingerprinting, Cloudflare, and JS cookie challenges block it.
- **Decision:** Consolidate all three into a single `JSearchScraper` (JSearch API
  via RapidAPI), parameterized by platform. Only LinkedIn is scraped directly
  (Playwright).
- **Consequences:** Reliable listings for three platforms through one adapter.
  Separate per-platform adapters were YAGNI — speculative generality with no
  practical benefit for a personal tool. Adds a JSearch API key + free-tier
  quota dependency.

## ADR-011: Dual evaluator provider support

- **Status:** Accepted
- **Context:** Provider outages, cost differences, and flexibility motivate more
  than one evaluator.
- **Decision:** Add `AnthropicEvaluator` (`claude-sonnet-4-5`) alongside the
  OpenAI default, selected via `EVALUATOR_PROVIDER` and built by an evaluator
  factory. Both return the identical `MatchResult` shape.
- **Consequences:** Cost comparison and outage fallback with zero core changes —
  a direct payoff of ADR-001. Prompts and parsing must be kept in sync across
  providers.

## ADR-012: Always deliver a RunReport

- **Status:** Accepted
- **Context:** Silent zero-result runs left users with no feedback when
  thresholds were aggressive.
- **Decision:** Always deliver a `RunReport` (email + CSV) on every run. Zero-
  result runs include the top-5 near-misses and a suggested lower threshold.
- **Consequences:** Closes the feedback loop without forcing users to read logs.
  Slightly more email/CSV volume.

## ADR-013: TOP_RESULTS is optional

- **Status:** Accepted
- **Context:** A forced default cap would silently hide qualifying results from
  users who never set the variable.
- **Decision:** `TOP_RESULTS` is optional; when unset, return all qualifying
  results above the threshold.
- **Consequences:** App is fully functional without it; capping is an opt-in
  delivery convenience.

## ADR-014: Date-posted filter via .env with CLI override

- **Status:** Accepted
- **Context:** Stale listings shouldn't reappear every run, but per-run freshness
  tuning should be easy.
- **Decision:** `DATE_POSTED` (default `3days`) in `.env`, overridable per run via
  a CLI argument; applied to both scrapers.
- **Consequences:** Sensible persistent default (`3days` balances freshness and
  coverage) with per-run flexibility, no `.env` edit required.

## ADR-015: Scraper selection via ACTIVE_SCRAPERS + ScraperFactory

- **Status:** Accepted
- **Context:** Hardcoded scraper instantiation gave no runtime control and
  invited typos.
- **Decision:** A `ScraperName` enum centralizes valid names; `ACTIVE_SCRAPERS`
  (`.env`) and `--scrapers` (CLI) choose active scrapers; `build_scrapers()`
  isolates instantiation from `main.py`.
- **Consequences:** Clean startup code, validated names, per-run flexibility.
  Scrapers must never be instantiated directly in `main.py`.

## ADR-016: Opt-in LLM cost tracking with configurable rates

- **Status:** Accepted
- **Context:** LLM spend needs visibility, but not every user wants the overhead,
  and providers change pricing frequently.
- **Decision:** `EvaluatorPort.evaluate()` returns `(MatchResult, input_tokens,
  output_tokens)`; `CostTracker`/`cost_estimator` (in `infra/`) own accumulation.
  Gated by `SHOW_COST_ESTIMATE=false` (default, zero overhead when off). Token
  rates are `.env` variables — no code change on price changes.
- **Consequences:** Cost visibility (pre-run estimate, per-job, run total, email
  footer, CSV columns) only when enabled; tracking stays out of the core domain.

## ADR-017: Configurable evaluation concurrency and delay

- **Status:** Accepted
- **Context:** TPM rate limits are tier-dependent; a fixed concurrency value is
  wrong for many users.
- **Decision:** `MAX_CONCURRENT_EVALUATIONS` (semaphore size, default `2`) and
  `EVALUATION_DELAY_SECONDS` (post-eval delay, default `1.0`) are `.env`-driven.
- **Consequences:** Users tune to their API tier without code changes; avoids 429
  TPM errors under normal conditions.

## ADR-018: In-process scheduling via APScheduler

- **Status:** Accepted
- **Context:** Scheduled Docker execution should not depend on host cron.
- **Decision:** Use APScheduler (`BlockingScheduler` + `CronTrigger`) inside the
  container, activated by `SCHEDULE_ENABLED=true`, with `SCHEDULE_CRON` and
  `SCHEDULE_TIMEZONE`. `SCHEDULE_ENABLED` is `.env`-only (containers have no
  interactive CLI).
- **Consequences:** Expressive cron scheduling with correct timezone/DST handling
  and no host dependency. The container runs indefinitely (`restart:
  unless-stopped`).

## ADR-019: Multiple search profiles via PROFILE_N_ prefix

- **Status:** Accepted
- **Context:** A user may want several independent searches per run.
- **Decision:** Numbered `PROFILE_N_*` env vars with `PROFILE_COUNT`; each profile
  builds its own service via `build_service()` and delivers its own report.
  Falls back to legacy single-search mode when `PROFILE_COUNT` is unset.
- **Consequences:** Multiple searches without code changes; results are easy to
  distinguish. Profiles run sequentially to avoid API flooding; a failing profile
  is logged and does not stop the others.

## ADR-020: main.py refactored into single-responsibility modules

- **Status:** Accepted
- **Context:** `main.py` had grown to ~170 lines mixing logging, arg parsing, CLI
  overrides, profile loading, immediate run, and result logging.
- **Decision:** Extract into focused modules — `cli/`, `infra/`, `bootstrap.py`,
  `runner.py` — leaving `main.py` a thin entrypoint. `bootstrap.py`/`runner.py`
  carry no CLI dependency so a future API entrypoint can reuse them.
- **Consequences:** Better testability and reuse. Never add logic directly to
  `main.py`.

## ADR-021: src/api/ reserved as a placeholder

- **Status:** Accepted
- **Context:** A future FastAPI entrypoint is anticipated.
- **Decision:** Create `src/api/` (only `__init__.py`) now so future API work
  follows the established structure without restructuring existing code.
- **Consequences:** Clear reservation; an empty stub package until implemented.
  (`src/evaluator/`, `src/scraper/`, `src/tools/` are unrelated leftover stubs.)
