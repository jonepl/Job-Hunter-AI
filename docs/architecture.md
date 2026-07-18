# Architecture Document
## Job Search Automation Agent

---

## 1. Overview

The Job Search Automation Agent is a Dockerized Python backend service that scrapes job listings from multiple platforms, evaluates each listing against a candidate resume using GPT-4o, and delivers ranked matches via email and CSV file output.

The system is designed using **Hexagonal Architecture (Ports and Adapters)** to ensure the core business logic is fully isolated from external dependencies such as job board scrapers, LLM providers, email services, and file output systems.

---

## 2. Architecture Pattern — Hexagonal Architecture

Hexagonal Architecture organizes the application into three distinct layers:

```
┌────────────────────────────────────────────────────────┐
│                    ADAPTERS (External)                 │
│                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │  Scrapers   │  │  Evaluator  │  │    Output      │  │
│  │  LinkedIn   │  │   OpenAI    │  │  Gmail SMTP    │  │
│  │  Indeed     │  │   GPT-4o    │  │  CSV File      │  │
│  │  Glassdoor  │  └──────┬──────┘  └───────┬────────┘  │
│  │  ZipRecruit │         │                 │           │
│  └──────┬──────┘         │                 │           │
│         │                │                 │           │
├─────────┼────────────────┼─────────────────┼───────────┤
│         │           PORTS (Interfaces)     │           │
│         ▼                ▼                 ▼           │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ ScraperPort │  │EvaluatorPort│  │  OutputPort    │  │
│  └──────┬──────┘  └──────┬──────┘  └───────┬────────┘  │
│         │                │                 │           │
├─────────┼────────────────┼─────────────────┼───────────┤
│         │            CORE DOMAIN           │           │
│         ▼                ▼                 ▼           │
│  ┌─────────────────────────────────────────────────┐   │
│  │              JobSearchService                   │   │
│  │         (Orchestration & Business Logic)        │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                             │
│         ┌────────────────┼────────────────┐            │
│         ▼                ▼                ▼            │
│      Job            Resume          MatchResult        │
│    (Entity)         (Entity)         (Entity)          │
└────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility |
|---|---|
| **Core Domain** | Business logic, domain entities, orchestration |
| **Ports** | Abstract interfaces defining contracts for external systems |
| **Adapters** | Concrete implementations of ports for each external system |

### Key Principle

No core domain code imports from adapters. All dependencies point inward — adapters depend on ports, ports define the domain contract, and the core domain has zero knowledge of external systems.

**This means:** swapping LinkedIn for a new job board, replacing GPT-4o with another LLM, or changing the email provider requires only a new adapter — the core logic is never touched.

### Driving adapters — CLI and FastAPI (ADR-021, ADR-026)

The scraper/evaluator/output adapters above are *driven* adapters (the core calls
them). There are also two **driving** adapters that call *into* the core: the **CLI**
(`src/main.py` → `cli/`) and the **FastAPI app** (`src/api/`). Both sit on the same
side of the hexagon over the identical services and `JobRepositoryPort` — FastAPI
reimplements no business logic; a route is a second way in, not a new brain. The
React SPA under `web/` is an HTTP client of that API. In production FastAPI serves
the built SPA at `/` and the JSON API under `/api` from the same origin.

The CLI has two modes: the default (no-subcommand) invocation runs a search; the
`mark` subcommand moves a stored job through its lifecycle
(`python -m src.main mark --job-id 7 --status applied --note "referred"`, plus
`--save` / `--unsave`). `mark` dispatches to `run_mark` (`src/mark_runner.py`),
which is argparse-free so the API's status write reuses the same repository path.
Only the six **human-set** statuses are selectable — machine states are never
user-assignable (ADR-025).

**API surface (as of W2).** All routes under `/api`, no business logic in the
router (ADR-026):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/jobs` | List — lean `JobSummary` cards, ranked strongest-first |
| `GET` | `/api/jobs/{id}` | Detail fan-out — `JobDetail` (breakdown, skills, status history); 404 if missing |
| `PATCH` | `/api/jobs/{id}/status` | `{status, note?}` → `set_status` + history row; 422 on a machine status |
| `PATCH` | `/api/jobs/{id}/saved` | `{saved}` → `set_saved` (no history row) |

The two `PATCH` routes are the web app's first mutations; the React client applies
them optimistically (ui-spec §8) and rolls back on error. No endpoint ever returns
generated-document content or raw resume text (ui-spec §7). Run history,
generation, settings, and resume-upload routes arrive with later stories.

```
   CLI  (src/main, src/cli) ─┐
   FastAPI (src/api)  ───────┼──▶  JobSearchService / JobRepositoryPort  ──▶  driven adapters
   React SPA (web/) ─HTTP─────┘
```

---

## 3. Project Structure

```
job-search-agent/
│
├── CLAUDE.md                            ← Auto-loaded agent guide (start here)
│
├── .claude/                             ← Agent Control System (Claude Code)
│   ├── rules/                           ← Topic-scoped conventions
│   │   ├── architecture.md
│   │   ├── scraping.md
│   │   ├── evaluation.md
│   │   ├── output-and-scheduling.md
│   │   ├── testing.md
│   │   ├── code-style.md
│   │   └── docker.md
│   ├── commands/                        ← Slash commands (setup, run-agent, …)
│   └── skills/                          ← Bundled workflows
│       ├── environment-setup/SKILL.md
│       ├── feature-development/SKILL.md
│       ├── add-job-source/SKILL.md
│       ├── debugging/SKILL.md
│       ├── testing/SKILL.md
│       ├── resume-evaluation/SKILL.md
│       └── docker/SKILL.md
│
├── docs/
│   ├── prd.md                           ← Product Requirements Document
│   ├── architecture.md                  ← This file
│   ├── adr.md                           ← Architecture Decision Records (living log)
│   ├── env.md                           ← Environment variable reference
│   └── resume/
│       └── resume.pdf                   ← Candidate resume (volume mounted)
│
├── src/
│   ├── main.py                          ← thin CLI entrypoint (search + mark dispatch)
│   ├── bootstrap.py                     ← profile loading
│   ├── runner.py                        ← immediate run logic
│   ├── mark_runner.py                   ← run_mark() — mark CLI backend (no argparse dep)
│   ├── scheduler.py                     ← APScheduler — cron-based multi-profile runner
│   ├── service_factory.py               ← Builds JobSearchService from SearchProfile
│   │
│   ├── api/                             ← FastAPI driving adapter (serves API + SPA)
│   │   ├── __init__.py
│   │   ├── main.py                      ← app factory (create_app); uvicorn entrypoint
│   │   ├── deps.py                      ← get_repository() — reuses build_repository()
│   │   ├── schemas.py                   ← JobSummary / JobDetail + PATCH bodies (camelCase)
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── jobs.py                  ← GET /api/jobs · GET/PATCH /api/jobs/{id}
│   │
│   ├── cli/                             ← CLI concerns
│   │   ├── __init__.py
│   │   ├── args.py                      ← argparse definition
│   │   └── overrides.py                 ← CLI override logic
│   │
│   ├── infra/                           ← infrastructure
│   │   ├── __init__.py
│   │   ├── logging.py                   ← logging config
│   │   ├── cost_tracker.py              ← Accumulates LLM token usage per run
│   │   └── cost_estimator.py            ← Pre-run static cost estimate
│   │
│   ├── core/
│   │   ├── domain/                      ← Pydantic entities
│   │   │   ├── __init__.py
│   │   │   ├── date_posted.py           ← DatePosted enum
│   │   │   ├── job.py                   ← Job entity
│   │   │   ├── resume.py                ← Resume entity
│   │   │   ├── match_result.py          ← MatchResult entity
│   │   │   ├── run_report.py            ← RunReport entity
│   │   │   ├── cost_estimate.py         ← CostEstimate — pre-run cost prediction
│   │   │   ├── run_cost.py              ← RunCost + EvaluationCost — actual run cost
│   │   │   ├── enrichment_result.py     ← EnrichmentResult — per-job pre-filter verdict
│   │   │   ├── enrichment_summary.py    ← EnrichmentSummary — run-level pre-filter surface
│   │   │   ├── fingerprint.py           ← Fingerprint + compute_fingerprint() (pure dedup key)
│   │   │   ├── stored_job.py            ← StoredJob — a persisted job + reused evaluation
│   │   │   ├── job_status.py            ← JobStatus enum + is_human_set (nine-state lifecycle)
│   │   │   ├── status_history_entry.py  ← StatusHistoryEntry — one lifecycle audit-trail row
│   │   │   ├── sighting.py              ← Sighting — one job seen on one platform
│   │   │   ├── scraper_name.py          ← ScraperName enum
│   │   │   └── search_profile.py        ← SearchProfile — per-profile config model
│   │   │
│   │   ├── ports/                       ← Abstract Base Class interfaces
│   │   │   ├── __init__.py
│   │   │   ├── scraper_port.py          ← ScraperPort ABC
│   │   │   ├── evaluator_port.py        ← EvaluatorPort ABC
│   │   │   ├── job_enrichment_port.py   ← JobEnrichmentPort ABC (pre-filter; Job-only, no Resume)
│   │   │   ├── job_repository_port.py   ← JobRepositoryPort ABC (persistence + dedup)
│   │   │   └── output_port.py           ← OutputPort ABC
│   │   │
│   │   └── services/                    ← Business logic orchestration
│   │       ├── __init__.py
│   │       └── job_search_service.py    ← JobSearchService
│   │
│   └── adapters/
│       ├── scrapers/                    ← One adapter per platform
│       │   ├── __init__.py
│       │   ├── linkedin.py
│       │   ├── jsearch.py
│       │   └── scraper_factory.py       ← Builds active scraper instances
│       │
│       ├── evaluator/                   ← LLM evaluation adapters
│       │   ├── __init__.py
│       │   ├── openai_evaluator.py
│       │   ├── anthropic_evaluator.py
│       │   ├── prompts.py               ← Shared evaluation prompt text
│       │   └── factory.py               ← Selects evaluator from EVALUATOR_PROVIDER
│       │
│       ├── enrichment/                  ← Optional pre-filter adapter
│       │   ├── __init__.py
│       │   ├── gemini_enrichment.py     ← Gemini pre-filter (fail-open, circuit breaker)
│       │   ├── prompts.py               ← Pre-filter prompt text
│       │   └── factory.py               ← Builds pre-filter from ENRICHMENT_* / GEMINI_*
│       │
│       ├── repository/                  ← SQLite persistence (JobRepositoryPort)
│       │   ├── __init__.py
│       │   ├── sqlite_repository.py     ← SQLiteJobRepository (WAL, busy_timeout, short commits)
│       │   ├── migrations.py            ← Forward-only runner (jobs + sightings + status_history)
│       │   └── factory.py               ← Builds the repo singleton from DB_PATH
│       │
│       └── output/                      ← Delivery adapters
│           ├── __init__.py
│           ├── email_output.py          ← Gmail SMTP adapter
│           └── file_output.py           ← CSV file adapter
│
web/                                     ← Job Hunter AI Web (Vite + React + TS SPA)
│
├── src/
│   ├── main.tsx                         ← React entry (ThemeProvider + QueryClientProvider)
│   ├── App.tsx                          ← page shell (header + JobList)
│   ├── api/
│   │   ├── client.ts                    ← typed fetch wrapper (the only place fetch is called)
│   │   └── types.ts                     ← generated from OpenAPI (npm run gen:types)
│   ├── hooks/                           ← React Query hooks (useJobs; useJob/useMarkStatus/useSaved — optimistic)
│   ├── components/                      ← ThresholdRail, ScoreChip, JobCard, ProviderBadges, StatusPill,
│   │                                       JobDetail, ScoreBreakdown, StatusDropdown, SaveStar, GenerationChip, ThemeToggle
│   ├── screens/                         ← JobList (list + detail pane; loading / empty / error states)
│   ├── lib/                             ← queryClient, theme, score (ADR-033), platforms, status (vocabulary)
│   └── styles/                          ← tokens.css (wired copy) + index.css (Tailwind)
├── tests/                              ← Jest + React Testing Library
├── vite.config.ts                       ← dev proxy /api → :8000
└── tailwind.config.cjs                  ← theme.extend derived from tokens.css (ADR-027)
│
tests/
│
├── unit/                                    ← mirrors src/ exactly
│   ├── test_bootstrap.py                    ← tests for load_profiles()
│   ├── test_runner.py                       ← tests for run_immediate()
│   ├── test_mark_runner.py                  ← tests for run_mark() (mark CLI backend)
│   ├── test_scheduler.py                    ← tests for run_all_profiles()
│   ├── test_main_args.py                    ← tests for main() argument wiring
│   ├── api/
│   │   └── test_jobs_router.py              ← tests for GET/PATCH /api/jobs[/{id}] (FastAPI TestClient)
│   ├── cli/
│   │   ├── test_args.py                     ← tests for parse_args()
│   │   └── test_overrides.py               ← tests for apply_cli_overrides()
│   ├── infra/
│   │   ├── test_logging.py                 ← tests for configure_logging()
│   │   ├── test_cost_tracker.py            ← tests for CostTracker
│   │   └── test_cost_estimator.py          ← tests for estimate_run_cost()
│   ├── core/
│   │   ├── domain/
│   │   │   ├── test_date_posted.py          ← tests for DatePosted enum
│   │   │   ├── test_job.py                  ← tests for Job entity
│   │   │   ├── test_resume.py               ← tests for Resume entity
│   │   │   ├── test_match_result.py         ← tests for MatchResult entity
│   │   │   ├── test_run_report.py           ← tests for RunReport entity
│   │   │   ├── test_cost_estimate.py        ← tests for CostEstimate entity
│   │   │   ├── test_run_cost.py             ← tests for RunCost / EvaluationCost entities
│   │   │   ├── test_enrichment_result.py    ← tests for EnrichmentResult entity
│   │   │   ├── test_enrichment_summary.py   ← tests for EnrichmentSummary entity
│   │   │   ├── test_fingerprint.py          ← tests for compute_fingerprint (raw→canonical table)
│   │   │   ├── test_stored_job.py           ← tests for StoredJob entity
│   │   │   ├── test_job_status.py           ← tests for JobStatus enum + is_human_set
│   │   │   ├── test_status_history_entry.py ← tests for StatusHistoryEntry entity
│   │   │   ├── test_sighting.py             ← tests for Sighting entity
│   │   │   ├── test_scraper_name.py         ← tests for ScraperName enum
│   │   │   └── test_search_profile.py       ← tests for SearchProfile model
│   │   │
│   │   ├── ports/
│   │   │   ├── test_scraper_port.py         ← tests for ScraperPort ABC
│   │   │   ├── test_evaluator_port.py       ← tests for EvaluatorPort ABC
│   │   │   ├── test_job_enrichment_port.py  ← tests for JobEnrichmentPort ABC (privacy boundary)
│   │   │   ├── test_job_repository_port.py  ← tests for JobRepositoryPort ABC
│   │   │   └── test_output_port.py          ← tests for OutputPort ABC
│   │   │
│   │   └── services/
│   │       └── test_job_search_service.py   ← tests for orchestration logic
│   │
│   └── adapters/
│       ├── scrapers/
│       │   ├── test_linkedin.py
│       │   ├── test_jsearch.py
│       │   └── test_scraper_factory.py
│       ├── evaluator/
│       │   ├── test_openai_evaluator.py
│       │   ├── test_anthropic_evaluator.py
│       │   └── test_factory.py
│       ├── enrichment/
│       │   ├── test_gemini_enrichment.py
│       │   └── test_factory.py
│       ├── repository/
│       │   ├── test_sqlite_repository.py
│       │   └── test_factory.py
│       └── output/
│           ├── test_email_output.py
│           └── test_file_output.py
│
├── conftest.py                              ← shared fixtures for all tests
│
│   (No integration/ suite or fixtures/ directory exists yet — unit tests only.
│    Integration coverage is deferred; see §13 and docs/prd.md §12.)
│
├── logs/                                ← Persistent log output (volume mounted)
├── output/                              ← CSV results output (volume mounted)
├── Dockerfile
├── docker-compose.yml
├── setup.sh
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 4. Domain Entities

All domain entities are defined as **Pydantic models** for automatic validation, type enforcement, and JSON serialization. Pydantic is chosen because scraped and LLM-generated data is inherently unreliable — validation at the boundary prevents malformed data from propagating through the system.

### `Job`
Represents a single job listing scraped from a platform.

```python
class Job(BaseModel):
    title: str
    company: str
    location: str
    url: str
    description: str
    platform: str
    scraped_at: datetime
```

### `Resume`
Represents the parsed candidate resume.

```python
class Resume(BaseModel):
    raw_text: str
    parsed_at: datetime
```

### `MatchResult`
Represents the evaluated match between a resume and a job listing.

```python
class MatchResult(BaseModel):
    job: Job
    score: int                    # 0–100
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str
```

### `ScraperName`
Enumeration of all supported job platform scrapers. Used to control which platforms are active at runtime via `ACTIVE_SCRAPERS` in `.env` or `--scrapers` CLI argument.

```python
class ScraperName(str, Enum):
    LINKEDIN     = "linkedin"
    INDEED       = "indeed"
    GLASSDOOR    = "glassdoor"
    ZIPRECRUITER = "ziprecruiter"

    @classmethod
    def from_string(cls, value: str) -> "ScraperName": ...
    # Case-insensitive parse; raises ValueError on unknown name

    @classmethod
    def parse_list(cls, value: str) -> list["ScraperName"]: ...
    # Parses comma-separated string, e.g. "linkedin,indeed"

    @classmethod
    def all(cls) -> list["ScraperName"]: ...
    # Returns all four ScraperName values
```

### `CostEstimate`
Represents a pre-run static cost estimate calculated from config before any API calls are made. Predicts the cost range based on maximum possible evaluations.

```python
class CostEstimate(BaseModel):
    max_jobs: int
    est_min_cost_usd: float
    est_max_cost_usd: float
    provider: str
    input_cost_per_1m: float
    output_cost_per_1m: float

    @property
    def formatted_range(self) -> str: ...
    # Returns "$0.1234 - $0.5678"
```

### `EvaluationCost`
Represents the token usage and cost for a single job evaluation.

```python
class EvaluationCost(BaseModel):
    job_title: str
    company: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
```

### `RunCost`
Represents the accumulated LLM cost across an entire pipeline run. Built from a list of `EvaluationCost` instances after all evaluations complete.

```python
class RunCost(BaseModel):
    evaluations: list[EvaluationCost]
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    provider: str
    jobs_evaluated: int

    @property
    def formatted_total(self) -> str: ...
    # Returns "$0.2134"

    @classmethod
    def from_evaluations(
        cls,
        evaluations: list[EvaluationCost],
        provider: str
    ) -> "RunCost": ...
```

### `RunReport`
Represents the full summary of a single pipeline run. Always produced regardless of whether any jobs passed the score threshold.

```python
class RunReport(BaseModel):
    qualifying_results: list[MatchResult]  # Jobs that passed threshold + TOP_RESULTS cap
    near_miss_results: list[MatchResult]   # Top 5 below threshold — only when qualifying is empty
    total_evaluated: int                   # Total jobs sent to LLM evaluator
    score_threshold: int                   # Threshold used this run
    top_results: int | None                # TOP_RESULTS cap used; None when not set
    active_scrapers: list[ScraperName]     # Scrapers active this run
    query: str                             # Search query used this run
    location: str                          # Location used this run
    run_at: datetime                       # Timestamp of run completion

    cost_estimate: CostEstimate | None   # None when SHOW_COST_ESTIMATE=false
    run_cost: RunCost | None             # None when SHOW_COST_ESTIMATE=false
    enrichment_summary: EnrichmentSummary | None  # None when the pre-filter did not run
    near_miss_band: int                  # fixed offset below threshold (ADR-033); default 15
    reused_count: int                    # jobs whose stored evaluation was reused (dedup hits)

    @property
    def has_qualifying_results(self) -> bool: ...
    # Returns True when qualifying_results is non-empty

    @property
    def near_miss_floor(self) -> int: ...
    # threshold - near_miss_band, floored at 0 (ADR-033)

    @property
    def suggested_threshold(self) -> int | None: ...
    # The near_miss_floor when there are near-misses; None otherwise (ADR-033 —
    # replaces the retired floor-the-lowest-of-five rule)
```

### `EnrichmentResult`
The pre-filter's verdict on a single job (see §7 — the optional Gemini pre-filter).
Advisory: whether a flagged job is actually skipped depends on `ENRICHMENT_MODE`.

```python
class EnrichmentResult(BaseModel):
    should_skip: bool   # True when the pre-filter judges the job obvious junk
    reason: str         # Always populated — a flag is never applied silently
    errored: bool       # True when this is a fail-open fallback, not a real judgement
```

### `EnrichmentSummary`
The run-level pre-filter decision surface, attached to `RunReport`. Shadow mode is
only useful if its output is a decision surface (ADR-022): this reports what would
have been skipped, how often that was wrong, and whether the run meets the written
criterion to graduate to `enforce`.

```python
class EnrichmentSummary(BaseModel):
    mode: str                          # "shadow" | "enforce"
    total_jobs: int                    # jobs the pre-filter inspected
    flagged_count: int                 # jobs flagged to skip
    evaluated_count: int               # jobs actually sent to the paid evaluator
    error_count: int                   # jobs the pre-filter could not assess (fail-open)
    false_skips: int | None            # shadow only: flagged jobs that scored >= threshold
    estimated_savings_usd: float | None
    circuit_broken: bool               # a quota/model breaker tripped mid-run

    @property
    def false_skip_rate(self) -> float | None: ...   # None in enforce / when nothing flagged

    @property
    def graduation_ready(self) -> bool: ...
    # True when shadow, 0 false-skips, 0 errors, >= 50 evaluated jobs
```

### `Fingerprint`
A job's deterministic identity for exact-match deduplication (ADR-024). Built by
the pure function `compute_fingerprint(company, title, location)` — no I/O — called
by both the persistence write path and the dedup check so they can never disagree.
Full normalization rules: `docs/build/vertical-story-split.md` §13.

```python
class Fingerprint(BaseModel):
    canon_company: str      # canonicalized identity fields
    canon_title: str
    canon_location: str
    version: int            # FINGERPRINT_VERSION; lets stale keys be recomputed

    @property
    def key(self) -> str | None: ...
    # "company|title|location", or None when any field is empty (dedup disabled)

# relation(a, b) -> "match" | "near_miss" | "distinct"
#   match     — all three canonical fields equal        (skip re-eval / add sighting)
#   near_miss — company + title equal, location differs (logged, never merged)
#   distinct  — company or title differs, or incomplete (dedup disabled)
```

### `StoredJob`
A job as persisted in the repository, returned by `JobRepositoryPort` lookups. On a
dedup hit the service reuses the stored `match_result` instead of paying the
evaluator again, and reads `seen_on` for the cross-provider read model. The
threshold and near-miss floor are stored per evaluation (ADR-033).

```python
class StoredJob(BaseModel):
    id: int
    company: str; title: str; location: str; url: str | None
    fingerprint: str | None            # canonical key; None disables dedup
    fingerprint_version: int
    canon_company: str; canon_title: str; canon_location: str
    match_result: MatchResult | None   # reused on a dedup hit
    threshold: int | None              # threshold in force at evaluation (ADR-033)
    near_miss_floor: int | None        # threshold - NEAR_MISS_BAND (ADR-033)
    description: str | None            # raw posting text — "About the role" (W2)
    status: JobStatus                  # lifecycle state (ADR-025); default new
    saved: bool                        # bookmark, independent of status
    first_seen_at: datetime; last_seen_at: datetime
    seen_on: list[str]                 # distinct platforms sighted on
```

### `JobStatus`
The nine-state job lifecycle (ADR-025), a `str` enum in
`src/core/domain/job_status.py`. Three **machine-set** states are assigned by the
pipeline (`new`, `evaluated`, `pre_filtered`); six **human-set** states are assigned
via the `mark` CLI (`applied`, `started`, `interviewing`, `offer`, `rejected`,
`not_interested`). `MACHINE_STATUSES` / `HUMAN_STATUSES` frozensets and
`is_human_set(status)` classify a state — the classification the no-clobber rule and
the pipeline's suppression step both read.

```python
class JobStatus(str, Enum):
    NEW = "new"; EVALUATED = "evaluated"; PRE_FILTERED = "pre_filtered"
    APPLIED = "applied"; STARTED = "started"; INTERVIEWING = "interviewing"
    OFFER = "offer"; REJECTED = "rejected"; NOT_INTERESTED = "not_interested"

# Transitions are permissive (any → any), recorded append-only in status_history.
# One hard domain rule: a machine write never clobbers a human-set status.
# `saved` is a boolean column, never a JobStatus member — a job can be saved AND
# applied.
```

### `StatusHistoryEntry`
One row of a job's append-only lifecycle audit trail (ADR-025), in
`src/core/domain/status_history_entry.py`. The detail screen renders these as the
job's action timeline; the creation row has `from_status` None.

```python
class StatusHistoryEntry(BaseModel):
    from_status: JobStatus | None   # None for the creation row
    to_status: JobStatus
    changed_at: datetime
    note: str | None
```

### `Sighting`
One observation of a job on one platform. A single job (one fingerprint) can be
sighted on several platforms — the set is the "seen on: linkedin, indeed" read
model surfaced in the report (CSV column + email line).

```python
class Sighting(BaseModel):
    platform: str            # scraper/source name
    url: str | None          # platform-specific URL, if known
    seen_at: datetime
```

---

## 5. Port Interfaces

Ports are defined as **Abstract Base Classes (ABC)** for explicit contract definition and runtime enforcement. Any adapter that fails to implement a required method raises an error immediately at instantiation — not silently at runtime.

### `ScraperPort`

```python
from abc import ABC, abstractmethod
from src.core.domain.job import Job

class ScraperPort(ABC):

    @abstractmethod
    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25
    ) -> list[Job]:
        """Fetch job listings from a platform."""
        ...
```

### `EvaluatorPort`

```python
from abc import ABC, abstractmethod
from src.core.domain.resume import Resume
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult

class EvaluatorPort(ABC):

    @abstractmethod
    async def evaluate(
        self,
        resume: Resume,
        job: Job,
        work_types: list[WorkType] | None = None,
    ) -> tuple[MatchResult, int, int]:
        """Evaluate a job listing against a resume.

        Returns a tuple of (MatchResult, input_tokens, output_tokens).
        Token counts are extracted from the API response metadata at
        no extra cost and made available for cost tracking.
        """
        ...
```

### `JobEnrichmentPort`

The optional pre-filter contract. **The signature is the privacy boundary** —
`enrich` accepts only a `Job` and never a `Resume`, so personal data is
structurally prevented from reaching the pre-filter adapter (ADR-022). Do not widen
this contract.

```python
from abc import ABC, abstractmethod
from src.core.domain.job import Job
from src.core.domain.enrichment_result import EnrichmentResult

class JobEnrichmentPort(ABC):

    @abstractmethod
    async def enrich(self, job: Job) -> EnrichmentResult:
        """Judge whether a job is obvious junk before paid evaluation.

        Implementations must be fail-open: any error returns
        should_skip=False so a pre-filter failure never drops a real job.
        """
        ...
```

### `JobRepositoryPort`

The persistence and deduplication contract (ADR-023). The core sees only this
port — it has no knowledge of SQLite. All writes flow through one instance so a
scheduled run and a browser mutation are serialized safely (ADR-034 §1).

```python
from abc import ABC, abstractmethod

class JobRepositoryPort(ABC):

    @abstractmethod
    def list_jobs(self) -> list[StoredJob]: ...
    # All stored jobs, ranked by score desc (unevaluated last) — backs GET /api/jobs

    @abstractmethod
    def get_job(self, job_id: int) -> StoredJob | None: ...
    # Single-row lookup — backs the mark CLI (resolve + display a job)

    @abstractmethod
    def set_status(self, job_id, to_status, note=None, *, machine=False) -> bool: ...
    # Guarded transition (ADR-025): idempotent no-op writes no history; a
    # machine=True write never clobbers a human-set status; else updates
    # jobs.status + appends a status_history row. Returns True iff it changed.

    @abstractmethod
    def set_saved(self, job_id: int, saved: bool) -> None: ...
    # Toggle the saved bookmark; idempotent, never writes history

    @abstractmethod
    def get_status_history(self, job_id: int) -> list[StatusHistoryEntry]: ...
    # A job's append-only status history, oldest-first — the detail timeline

    @abstractmethod
    def find_by_fingerprint(self, key: str) -> StoredJob | None: ...
    # Exact fingerprint lookup — a hit reuses the stored evaluation

    @abstractmethod
    def find_near_misses(
        self, canon_company: str, canon_title: str, exclude_key: str | None = None
    ) -> list[StoredJob]: ...
    # Same company + title, different location — logged, never merged

    @abstractmethod
    def save_job(self, job, fingerprint, match_result, threshold,
                 near_miss_floor, seen_at) -> StoredJob: ...
    # Persist a new evaluation (short per-job commit) + first sighting

    @abstractmethod
    def record_sighting(self, job_id, platform, url, seen_at) -> None: ...
    # Idempotent per (job, platform); refreshes last_seen_at

    @abstractmethod
    def get_seen_on(self, job_id: int) -> list[str]: ...
    # Distinct platforms a job was sighted on
```

**Schema (migration 1 — B1).** `jobs` (raw + canonical fields, evaluation, and
`fingerprint` with a **partial UNIQUE index** `WHERE fingerprint IS NOT NULL` so
many dedup-disabled NULL keys can coexist) and `sightings` (one row per
`(job_id, platform)`). Stdlib `sqlite3`, WAL mode, `data/agent.db`. Each story adds
only the tables it needs; a `schema_migrations` table records what has run.

**Schema (migration 2 — C).** Adds `status TEXT NOT NULL DEFAULT 'evaluated'` and
`saved INTEGER NOT NULL DEFAULT 0` to `jobs`, and creates `status_history`
(`id`, `job_id` FK → `jobs` ON DELETE CASCADE, `from_status`, `to_status`, `note`,
`changed_at`) — the append-only audit trail behind the lifecycle (ADR-025). The
migration backfills one creation history row per existing job
(`NULL → its status` at `first_seen_at`) so the trail is complete.

### `OutputPort`

```python
from abc import ABC, abstractmethod
from src.core.domain.match_result import MatchResult

class OutputPort(ABC):

    @abstractmethod
    async def deliver(
        self,
        results: list[MatchResult]
    ) -> None:
        """Deliver ranked match results."""
        ...
```

---

## 6. Core Service — `JobSearchService`

`JobSearchService` is the central orchestrator. It accepts port interfaces as constructor arguments (**dependency injection**) and coordinates the full pipeline.

```
Scheduler (if SCHEDULE_ENABLED=true)
    → On cron trigger
    → For each SearchProfile
    → build_service(profile)
    → service.run(profile params)
    → RunReport delivered per profile

Immediate mode (SCHEDULE_ENABLED=false)
    → Load all profiles
    → For each SearchProfile
    → build_service(profile)
    → service.run(profile params)
    → RunReport delivered per profile
    → Exit

JobSearchService.run(query, location, threshold, top_results)
        │
        ├── 1. Parse resume from PDF
        │
        ├── 2. Scrape all platforms asynchronously
        │       ├── LinkedInAdapter.fetch_jobs()
        │       ├── IndeedAdapter.fetch_jobs()
        │       ├── GlassdoorAdapter.fetch_jobs()
        │       └── ZipRecruiterAdapter.fetch_jobs()
        │
        ├── 2.5 (Optional) Pre-filter — JobEnrichmentPort, only when enabled
        │       ├── Gemini flags obvious junk (Job only — resume never passed)
        │       ├── Throttled: ENRICHMENT_MAX_CONCURRENT + ENRICHMENT_DELAY_SECONDS
        │       ├── shadow: evaluate everything, measure would-be skips (false-skip rate)
        │       ├── enforce: withhold flagged jobs from evaluation
        │       └── Fail-open; quota/model circuit breaker; EnrichmentSummary → RunReport
        │
        ├── 2.6 Deduplicate — JobRepositoryPort (compute_fingerprint per job)
        │       ├── Prior-run hit → reuse stored score (never re-evaluated) + add sighting
        │       ├── Human-acted hit (status is human-set) → sighting recorded, but the
        │       │     job is SUPPRESSED from this run's report (ADR-025); status untouched
        │       ├── Same posting on N platforms this run → grouped, evaluated once
        │       ├── Near-miss (company+title equal, location differs) → logged, never merged
        │       └── Incomplete fingerprint → dedup disabled, evaluated fresh
        │
        ├── 3. Evaluate each new (non-reused) job against resume (GPT-4o)
        │       ├── Semaphore limits concurrent calls to MAX_CONCURRENT_EVALUATIONS
        │       ├── EVALUATION_DELAY_SECONDS applied after each evaluation
        │       ├── Token usage extracted from API response metadata
        │       ├── CostTracker.record() called per job when SHOW_COST_ESTIMATE=true
        │       └── OpenAIEvaluatorAdapter.evaluate() → tuple[MatchResult, int, int]
        │
        ├── 3.5 Persist each new evaluation (threshold + near_miss_floor) + sightings;
        │        combine reused + new results
        │
        ├── 4. Sort all evaluated by score descending
        │
        ├── 5. Filter qualifying — above score threshold
        │
        ├── 6. Apply TOP_RESULTS cap if set
        │
        ├── 7. If zero qualifying — collect near-misses in [threshold-NEAR_MISS_BAND, threshold)
        │
        ├── 8. Build RunReport
        │
        ├── 9. Deliver RunReport to all output adapters
        │       ├── EmailOutputAdapter.deliver(report)
        │       └── FileOutputAdapter.deliver(report)
        │
        └── 10. Return RunReport
```

**Technical Terms:** `Dependency Injection`, `Async Pipeline`, `Score Threshold Filtering`

---

## 7. Adapters

### Scraper Adapters

| Adapter | Platform | Method | Notes |
|---|---|---|---|
| `LinkedInScraper` | LinkedIn | Playwright | JavaScript-rendered page. Supports `f_TPR` date posted filter and `f_WT` work type filter. |
| `JSearchScraper` | Indeed, Glassdoor, ZipRecruiter | JSearch API (RapidAPI) | Bot detection makes direct scraping non-viable for all three platforms. Supports `date_posted` param. `remote_jobs_only` for work type. |

All scraper adapters:
- Implement `ScraperPort`
- Apply a minimum 2 second delay between requests
- Handle HTTP errors, timeouts, and malformed responses gracefully
- Return validated `Job` Pydantic models

Active scrapers are controlled via `ACTIVE_SCRAPERS` in `.env` or the `--scrapers` CLI argument. `ScraperFactory` (`src/adapters/scrapers/scraper_factory.py`) builds the active scraper instances at startup — scrapers are never instantiated directly in `main.py`.

### Evaluator Adapters

| Adapter | Provider | Model | Notes |
|---|---|---|---|
| `OpenAIEvaluator` | OpenAI API | gpt-4o | Default, uses `response_format` strict mode |
| `ClaudeEvaluator` | Anthropic API | claude-sonnet-4-5 | Alternative, uses prompt-based JSON enforcement |

Both adapters:
- Implement `EvaluatorPort`
- Send resume text and job description to the LLM for scoring
- Parse and validate LLM response as a `MatchResult` Pydantic model
- Handle API errors gracefully — return a default low-score result on failure
- Return identical `MatchResult` output structure
- Select via `EVALUATOR_PROVIDER` in `.env` (`openai` or `anthropic`)

### Output Adapters

| Adapter | Delivery Method | Format |
|---|---|---|
| `EmailOutputAdapter` | Gmail via SMTP (smtplib) | HTML email |
| `FileOutputAdapter` | Local filesystem | CSV file |

Both implement `OutputPort`. CSV output is written to `output/results_<timestamp>.csv` which is persisted via Docker volume mount.

---

## 8. Asynchronous Scraping

All four platform scrapers run **concurrently** using Python `asyncio`. This reduces total scraping time from sequential (sum of all platform times) to approximately the time of the slowest single platform.

```python
import asyncio

results = await asyncio.gather(
    linkedin.fetch_jobs(query, location),
    indeed.fetch_jobs(query, location),
    glassdoor.fetch_jobs(query, location),
    ziprecruiter.fetch_jobs(query, location)
)
```

**Technical Terms:** `asyncio`, `Concurrent Execution`, `asyncio.gather`, `Async/Await`

---

## 9. Trigger Mechanism

The agent supports two trigger modes:

| Mode | Mechanism | How To Use |
|---|---|---|
| **Immediate** | Run once and exit | `python -m src.main` (SCHEDULE_ENABLED=false or not set) |
| **Scheduled** | APScheduler inside container runs indefinitely | `docker-compose up` (SCHEDULE_ENABLED=true) |

Immediate mode is used for local testing and manual runs. Scheduled mode is
used for Docker-based automated execution — APScheduler runs on SCHEDULE_CRON
indefinitely inside the container with no host cron dependency.

**Technical Terms:** `Immediate Mode`, `APScheduler`, `BlockingScheduler`, `CronTrigger`

---

## 10. Logging

The application uses Python's built-in `logging` module with two handlers:

| Handler | Output | Format |
|---|---|---|
| `StreamHandler` | Console (stdout) | Human-readable |
| `FileHandler` | `logs/agent_<timestamp>.log` | Structured text |

Log files are persisted via Docker volume mount and survive container restarts.

**Log levels used:**
- `INFO` — pipeline start, platform scrape counts, evaluation scores, delivery confirmation
- `WARNING` — missing fields in scraped data, LLM response anomalies
- `ERROR` — scraper failures, API errors, email delivery failures

**Technical Terms:** `StreamHandler`, `FileHandler`, `Log Level`, `Structured Logging`

---

## 11. Containerization

### Single Container Architecture

The entire application runs in a **single Docker container** managed by `docker-compose`.
A **multi-stage build** (ADR-021) first builds the React SPA in a Node stage, then copies
the static bundle into the Python image; FastAPI serves it at `/` alongside the API.

```
Docker Container
├── Python 3.10 runtime
├── Application source code (src/) + built SPA (web/dist)
├── Playwright + browser binaries (for CLI scraper runs)
└── All Python dependencies

Volume Mounts (persist outside container)
├── docs/resume/     ← Resume PDF input
├── output/          ← CSV results output
├── logs/            ← Application logs
└── data/            ← SQLite store (data/agent.db)
```

**Two entrypoints, one image.** The container's default command is the **web server**
(uvicorn). A **CLI run** reuses the same image but overrides the command
(`docker compose run --rm agent python -m src.main …`) and never boots the server.

### `Dockerfile` (outline)

```dockerfile
# Stage 1 — build the SPA
FROM node:22-slim AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2 — Python app (serves API + SPA; also the CLI entrypoint)
FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ...            # Playwright system deps
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install --with-deps
COPY src/ ./src/
COPY --from=frontend /web/dist ./web/dist               # SPA served at / by FastAPI

# Bind 0.0.0.0 in-container; compose publishes only to 127.0.0.1 (ADR-034 §2)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml` (outline)

```yaml
services:
  agent:
    build: .
    env_file: .env
    ports:
      - "127.0.0.1:8000:8000"    # loopback only — the app has no auth (ADR-034 §2)
    volumes:
      - ./docs/resume:/app/docs/resume
      - ./output:/app/output
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
```

Reach the app at `http://127.0.0.1:8000` (SPA at `/`, API under `/api`).

**Technical Terms:** `Dockerfile`, `docker-compose`, `Volume Mount`, `env_file`, `Slim Base Image`

---

## 12. Environment Variables

All secrets and configuration values are injected at runtime via `.env`. See `docs/env.md` for the full reference.

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Yes | GPT-4o evaluation |
| `ANTHROPIC_API_KEY` | Conditional | Required when `EVALUATOR_PROVIDER=anthropic` — API access for `AnthropicEvaluator` (claude-sonnet-4-5) |
| `GMAIL_ADDRESS` | Yes | SMTP sender address |
| `GMAIL_APP_PASSWORD` | Yes | Gmail App Password for SMTP |
| `EMAIL_RECIPIENT` | Yes | Results delivery address |
| `SCORE_THRESHOLD` | Yes | Minimum match score (default: 75). When no jobs meet this threshold a zero results report is delivered with top 5 near-miss jobs and a suggested lower threshold value. |
| `TOP_RESULTS` | No | When set caps qualifying results delivered after score filtering. When not set all jobs above SCORE_THRESHOLD are returned. |
| `JSEARCH_API_KEY` | Optional | Fallback job listings API |
| `EVALUATOR_PROVIDER` | Optional | Selects evaluator: `openai` or `anthropic` (default: `openai`) |
| `MAX_CONCURRENT_EVALUATIONS` | No | Max concurrent LLM evaluation requests (default: `2`) |
| `EVALUATION_DELAY_SECONDS` | No | Seconds delay between evaluations to manage TPM rate limits (default: `1.0`) |
| `SHOW_COST_ESTIMATE` | No | Enable cost tracking and visibility (default: `false`) |
| `CORS_ALLOW_ORIGINS` | No | Comma-separated origins the API allows (dev only; default `http://localhost:5173`) |
| `SPA_DIST_DIR` | No | Directory of the built SPA that FastAPI serves at `/` (default `web/dist`) |
| `OPENAI_INPUT_COST_PER_1M` | No | GPT-4o input token rate per million tokens in USD (default: `2.50`) |
| `OPENAI_OUTPUT_COST_PER_1M` | No | GPT-4o output token rate per million tokens in USD (default: `10.00`) |
| `ANTHROPIC_INPUT_COST_PER_1M` | No | claude-sonnet-4-5 input token rate per million tokens in USD (default: `3.00`) |
| `ANTHROPIC_OUTPUT_COST_PER_1M` | No | claude-sonnet-4-5 output token rate per million tokens in USD (default: `15.00`) |

---

## 13. Testing Strategy

**As-built:** the current suite is **unit tests only**, under `tests/unit/`,
mirroring the `src/` directory structure exactly. There is no `tests/integration/`
suite and no `tests/fixtures/` directory today — integration coverage is a
deferred goal (see Known Divergences and `docs/prd.md` §12). The unit convention
below is enforced; the integration column describes the intended shape if/when it
is added.

### Test Type Responsibilities

| | Unit Test (as-built) | Integration Test (deferred) |
|---|---|---|
| **What it tests** | Module in complete isolation | Module interacting with its dependencies |
| **External calls** | All mocked — no real APIs or files | Real file I/O, real API response shapes |
| **Speed** | Very fast — milliseconds | Slower — seconds |
| **Scope** | One function or class | One adapter end-to-end |
| **Failures reveal** | Logic bugs in your code | Compatibility bugs with external systems |

### Example — LinkedInScraper unit test

`tests/unit/adapters/scrapers/test_linkedin.py`:
- Mock the Playwright browser entirely
- `fetch_jobs()` returns a list of validated `Job` Pydantic models
- `fetch_jobs()` handles a timeout gracefully
- `fetch_jobs()` handles malformed HTML gracefully
- The 2-second rate-limit delay is applied
- No real browser, no real network call

### Shared Fixtures — `conftest.py`

Shared test data is defined in `tests/conftest.py` and available
to all tests automatically via pytest fixture injection.
```python
# tests/conftest.py

import pytest
from src.core.domain.job import Job
from src.core.domain.resume import Resume
from src.core.domain.match_result import MatchResult
from datetime import datetime

@pytest.fixture
def sample_job():
    return Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="We need a Python expert...",
        platform="linkedin",
        scraped_at=datetime.now()
    )

@pytest.fixture
def sample_resume():
    return Resume(
        raw_text="Experienced Python developer with 5 years...",
        parsed_at=datetime.now()
    )

@pytest.fixture
def sample_match_result(sample_job):
    # NOTE: MatchResult also requires the scoring-rubric fields
    # (seniority_level, years_experience_detected, hire_recommendation, and a
    # 9-category score_breakdown). See src/core/domain/match_result.py.
    return MatchResult(
        job=sample_job,
        score=85,
        matched_skills=["Python", "REST APIs"],
        missing_skills=["Kubernetes"],
        summary="Strong match with a gap in container orchestration.",
        # ... rubric fields omitted here for brevity
    )
```

### Running Tests
```bash
# Run the unit suite (the only suite that exists today)
pytest tests/unit/ -v

# Run a single layer
pytest tests/unit/core/domain/ -v

# Run tests for a specific module
pytest tests/unit/adapters/scrapers/test_linkedin.py -v
```

All tests must pass before committing any code. No test ever
calls a real external API.

---

## 14. Phase Roadmap

### Phase 1 — Local Docker (Current)
- Linear async Python pipeline
- Single Docker container
- Immediate mode and APScheduler scheduled mode both supported. SCHEDULE_ENABLED controls which mode runs.
- Multi-profile search via PROFILE_N_ variables in .env
- CSV file + Gmail SMTP output per profile
- All four platform scrapers

### Phase 2 — Cloud Deployment + Orchestration
- Migrate to cloud hosting (TBD provider)
- Introduce LangGraph for parallel scraping and conditional branching
- Native cloud scheduling replaces host cron
- Persistent database replaces CSV file output
- Monitoring and alerting

---

## 15. Architecture Decision Records (ADR)

The significant architectural decisions for this project — with their context,
choice, and consequences — are maintained as a living log in
[docs/adr.md](adr.md). New decisions are appended there rather than in this file.

Key decisions at a glance (see `docs/adr.md` for full records):

| ADR | Decision |
|---|---|
| 001 | Hexagonal Architecture (Ports & Adapters) |
| 002 | Pydantic models for all domain entities |
| 003 | Port interfaces as Abstract Base Classes |
| 004 | Asynchronous scraping with asyncio |
| 005 | OpenAI GPT-4o as the default evaluator |
| 006 | Gmail SMTP for email delivery |
| 007 | CSV as the file output format |
| 008 | Single Docker container via docker-compose |
| 009 | Console + file logging |
| 010 | JSearch API for Indeed, Glassdoor, ZipRecruiter (one adapter) |
| 011 | Dual evaluator provider support (OpenAI + Anthropic) |
| 012 | Always deliver a RunReport |
| 013 | TOP_RESULTS is optional |
| 014 | Date-posted filter via .env with CLI override |
| 015 | Scraper selection via ACTIVE_SCRAPERS + ScraperFactory |
| 016 | Opt-in LLM cost tracking with configurable rates |
| 017 | Configurable evaluation concurrency and delay |
| 018 | In-process scheduling via APScheduler |
| 019 | Multiple search profiles via PROFILE_N_ prefix |
| 020 | main.py refactored into single-responsibility modules |
| 021 | src/api/ reserved as a placeholder |
| 022 | Gemini pre-filter stage behind a JobEnrichmentPort |
| 023 | SQLite persistence behind a JobRepositoryPort |
| 024 | Exact-fingerprint deduplication on a normalized key |
| 025 | Job lifecycle with permissive transitions and append-only history |
| 026 | FastAPI as a driving adapter, parallel to the CLI |
| 027 | React 18 + TypeScript + Vite frontend with React Query |
