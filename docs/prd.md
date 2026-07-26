# Product Requirements Document

## Job Search Automation Agent

**Version:** 1.1
**Date:** 2026-03-16
**Status:** Draft

---

## 1. Overview

The Job Search Automation Agent is a Dockerized Python backend service that automates the end-to-end process of finding relevant job listings. It scrapes job postings from multiple platforms, evaluates each listing against a candidate resume using OpenAI GPT-4o, ranks the results by relevance score, and delivers the top matches via email — all without manual intervention.

The service is built on Hexagonal Architecture (Ports and Adapters), keeping core domain logic fully isolated from external dependencies. Each platform scraper, the LLM evaluator, and the output delivery mechanism are all independent adapters that can be swapped or extended without touching the core.

---

## 2. Problem Statement

Manually searching for jobs across multiple platforms is time-consuming and repetitive. A candidate must:

- Visit LinkedIn, Indeed, Glassdoor, and ZipRecruiter separately
- Read each job description individually
- Manually assess whether each role aligns with their experience and resume

This process is inefficient, inconsistent, and does not scale. There is no single tool that aggregates, filters, and ranks results intelligently against a specific candidate profile.

---

## 3. Goals

- Automatically scrape job listings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter
- Parse and extract text from a candidate's PDF resume
- Evaluate each job description against the resume using GPT-4o
- Score and rank results by relevance
- Return only jobs that meet a configurable relevance threshold (default: 70)
- Deliver results via SMTP email to the configured recipient
- Save results to a structured output file that persists after the container stops
- Run end-to-end without manual intervention once started

---

## 4. Target User

A single job seeker running the service locally via Docker. The user mounts their resume and output directory as volumes, sets environment variables, and triggers the service manually. They receive a curated ranked list of job matches by email.

---

## 5. Architecture Overview

The service follows **Hexagonal Architecture** (Ports and Adapters). Core domain logic is fully isolated from all external integrations. Adapters implement defined port interfaces and are injected at runtime.

### Dependency Direction

```
Adapters → Ports ← Core Domain
```

Core domain code never imports from adapters. All dependencies point inward.

### Project Structure

```
src/
├── core/
│   ├── domain/          # Entities: Job, Resume, MatchResult
│   ├── ports/           # Interfaces: ScraperPort, EvaluatorPort, OutputPort
│   └── services/        # JobSearchService — orchestrates the pipeline
└── adapters/
    ├── scrapers/         # linkedin.py, jsearch.py
    ├── evaluator/        # openai_evaluator.py
    └── output/           # email_output.py, file_output.py
```

### Ports

| Port | Responsibility |
|---|---|
| `ScraperPort` | Defines the interface each platform scraper must implement |
| `EvaluatorPort` | Defines the interface for resume-to-job evaluation and scoring |
| `OutputPort` | Defines the interface for result delivery (email, file) |

### Adapters

| Adapter | Port | Notes |
|---|---|---|
| `LinkedInScraper` | `ScraperPort` | Playwright — JS-rendered |
| `JSearchScraper` | `ScraperPort` | JSearch API (RapidAPI) — Indeed, Glassdoor, ZipRecruiter |
| `OpenAIEvaluator` | `EvaluatorPort` | GPT-4o via OpenAI SDK (default) |
| `ClaudeEvaluator` | `EvaluatorPort` | claude-sonnet-4-5 via Anthropic SDK (alternative) |
| `EmailOutput` | `OutputPort` | SMTP delivery |
| `FileOutput` | `OutputPort` | Structured file — persisted via volume mount |

---

## 6. Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM | OpenAI GPT-4o (default evaluator) or Anthropic claude-sonnet-4-5 (alternative evaluator) — provider switchable via `EVALUATOR_PROVIDER` in `.env` |
| JS-rendered scraping | Playwright (LinkedIn) |
| API-based scraping | JSearch API (RapidAPI) for Indeed, Glassdoor, ZipRecruiter |
| Resume parsing | PyPDF2 |
| Secret management | python-dotenv |
| Containerization | Docker + docker-compose |
| Email delivery | SMTP |
| Orchestration (Phase 2) | LangGraph |

---

## 7. Features

### Inputs

| Input | Description |
|---|---|
| Resume | PDF file injected via Docker volume mount at `docs/resume/resume.pdf` |
| Search query | e.g. `"Senior Python Developer"` |
| Location | e.g. `"Remote"` or `"Miami, FL"` |
| Score threshold | Configurable minimum match score (default: `70`) |

### Scraping

- Scrape job listings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter
- Use Playwright for LinkedIn (JavaScript-rendered, direct scraping)
- Use JSearch API (RapidAPI) for Indeed, Glassdoor, and ZipRecruiter — bot detection makes direct scraping non-viable for all three platforms
- Enforce a minimum 2-second delay between requests
- Cap results at 50 listings per platform per run
- Handle HTTP errors, timeouts, and empty responses gracefully

### Resume Evaluation

- Parse the candidate's PDF resume using PyPDF2
- Cache extracted resume text — do not re-parse on every run
- Send each job description and resume to GPT-4o for relevance scoring
- Each result includes: title, company, location, URL, score, matched skills, missing skills, and a summary

### Pre-filter (Gemini, optional)

- An optional cheap pre-filter stage sits **between scraping and evaluation** and
  flags obviously irrelevant postings before any paid, resume-aware evaluation
  runs. Enabled via `ENRICHMENT_ENABLED=true`; disabled by default with zero
  overhead.
- The pre-filter **never sees the resume** — it inspects only the job listing.
  This is enforced structurally by the `JobEnrichmentPort` signature, not by
  convention.
- **Fail-open:** any pre-filter error lets the job proceed to normal evaluation.
  A Gemini quota exhaustion trips a circuit breaker that skips the stage for the
  rest of the run.
- **Skip-but-log:** flagged jobs are never dropped silently — every flag records a
  reason. `ENRICHMENT_MODE` (default `shadow`) evaluates everything while
  measuring what *would* have been skipped; `enforce` actually withholds flagged
  jobs from the evaluator.
- The run report surfaces the **false-skip rate** (flagged jobs that nonetheless
  scored at/above threshold) and estimated savings, so precision can be verified
  before trusting the filter. Graduate to `enforce` once the false-skip rate is 0
  across ≥50 evaluated jobs.

### Ranking & Filtering

- Rank all evaluated jobs by relevance score (descending)
- Filter out any jobs below the configured score threshold
- Returns top TOP_RESULTS ranked job matches above SCORE_THRESHOLD when TOP_RESULTS is set. Returns all qualifying matches when TOP_RESULTS is not set.

### Configurable Scraper Selection

- Control which job platforms are scraped via `ACTIVE_SCRAPERS` in `.env`
- Override per run via `--scrapers` CLI argument
- Supports any combination of: `linkedin`, `indeed`, `glassdoor`, `ziprecruiter`
- Invalid scraper names caught at startup with clear error message
- Empty scraper list caught at startup with clear error message

### Configurable Evaluator Model

- Select the evaluator provider via `EVALUATOR_PROVIDER` (`openai` or `anthropic`)
- Each provider has a built-in default model (`gpt-4o` / `claude-sonnet-4-5`)
- Override the default via `EVALUATOR_MODEL` in `.env`, or per run via the
  `--evaluator-model` CLI argument (CLI wins over `.env`)
- The chosen model is logged at evaluator construction
- An invalid/nonexistent model name **fails the run fast** with a clear message
  (immediate mode exits non-zero; scheduled mode aborts that trigger) rather than
  silently scoring every job 0 — a config typo is fatal, not a transient error

### Multi-Profile Search

- Multiple search profiles configured via `PROFILE_N_` variables in `.env`
- Each profile runs independently with its own query, location, work type, scrapers, and thresholds
- Each profile delivers its own RunReport email and CSV
- `PROFILE_COUNT` sets the number of active profiles
- Falls back to legacy `SEARCH_QUERY` single search mode when `PROFILE_COUNT` is not set

### Scheduled Execution

- In-process APScheduler activated via `SCHEDULE_ENABLED=true` in `.env`
- Cron expression configured via `SCHEDULE_CRON` in `.env`
- Timezone configured via `SCHEDULE_TIMEZONE` in `.env`
- Runs all profiles on each scheduled trigger
- Container runs indefinitely with `restart: unless-stopped`
- Immediate mode (`SCHEDULE_ENABLED=false`) runs all profiles once and exits

### Always-On Run Report

- A report is always delivered after every run regardless of results
- Qualifying results: full ranked results with score breakdowns
- Zero qualifying results: zero results report with top 5 near-miss jobs, explanation, and threshold suggestion
- Near-miss results shown in condensed format — no score breakdown table
- TOP_RESULTS is optional — when not set all qualifying results are returned

### Output

- Save ranked results to a structured output file persisted via Docker volume mount
- Deliver results via SMTP email to the configured recipient

### LLM Cost Visibility

- Pre-run cost estimate shown at startup per profile when `SHOW_COST_ESTIMATE=true`
- Estimate shows max jobs to evaluate and predicted cost range in USD
- Actual token usage tracked per evaluation from API response metadata
- Per-job cost logged during evaluation
- Cumulative cost summary logged at run completion
- Cost summary included in email footer
- Cost columns included in CSV output
- All cost tracking disabled by default (`SHOW_COST_ESTIMATE=false`) for zero performance overhead
- Token rates configurable via `.env` — no code change needed when providers adjust pricing

### LLM Rate Limiting

- Concurrent evaluation requests controlled via `MAX_CONCURRENT_EVALUATIONS`
- Configurable delay between evaluations via `EVALUATION_DELAY_SECONDS`
- Prevents TPM rate limit errors when evaluating large job sets

---

## 8. Success Criteria

- Agent completes a full run end-to-end without manual intervention
- Returns top TOP_RESULTS ranked job matches above SCORE_THRESHOLD when TOP_RESULTS is set. Returns all qualifying matches when TOP_RESULTS is not set.
- Only returns matches scoring above the configurable threshold
- A report is always delivered — email and CSV written on every run including zero-result runs
- Delivers results via email to the configured recipient
- Saves results to an output file that persists after the container stops
- Core domain logic is fully testable without real scrapers or APIs
- All LLM calls handle API errors gracefully with try/except
- When `SHOW_COST_ESTIMATE=true` cost estimate appears before each profile run
- Actual LLM cost appears in run completion log, email footer, and CSV
- No 429 TPM rate limit errors under normal operating conditions

---

## 9. Constraints

- Must be free or low-cost to run
- Minimize paid API usage — use open-source libraries where possible
- Playwright browser binaries must run inside the Docker container
- Resume and output files are managed via Docker volume mounts — not baked into the image
- No cloud infrastructure costs in Phase 1
- No more than 50 results scraped per platform per run
- LLM API rate limits managed via configurable concurrency and delay settings — no manual intervention needed

---

## 10. Project Phases

### Phase 1 — Local Docker (Current)

A sequential linear pipeline deployed locally via docker-compose:

1. Accept inputs: query, location, resume path, score threshold
2. Scrape job listings from all four platforms
3. Parse resume text from PDF
4. Evaluate each job against the resume via GPT-4o
5. Score, filter, and rank results
6. Save results to output file
7. Deliver results via email

Immediate mode and APScheduler scheduled mode both supported. SCHEDULE_ENABLED controls which mode runs.

### Phase 2 — Cloud Deployment + Orchestration

- Migrate to cloud hosting
- Introduce LangGraph for parallel scraping across platforms and conditional branching (e.g. fallback on scrape failure)
- Add scheduling for automated runs

---

## 11. Out of Scope (Phase 1)

- ~~No web UI or dashboard~~ **Being superseded (W track — ADR-021/026/027).** W1
  landed the first screen: a FastAPI driving adapter (`src/api/`, serving `GET
  /api/jobs`) and a React SPA (`web/`) that lists persisted jobs with the score/
  threshold rail. Served same-origin by FastAPI, published on loopback only. **W2
  added the job detail pane and the first browser mutations** — `GET
  /api/jobs/{id}` fans out the nine-category breakdown, skills, and status history;
  `PATCH /api/jobs/{id}/status` and `/saved` let you mark status (with the
  reactivation soft-confirm) and bookmark a job from the UI, applied optimistically
  (ADR-025). **W3 added the status filter views** — the list opens on the **Triage**
  queue (`new`/`evaluated`), with **Pipeline** (`applied`/`started`/`interviewing`),
  **All**, and **Saved** one tap away, a visible clearable filter chip, and a live
  `N active · M total` count. Filtering is client-side over the single cached job
  list (no backend change) with a distinct filtered-empty state per view. Deferred:
  the per-run pre-filter count (needs run persistence — no runs table yet) and the
  persistent left-rail nav (arrives with the profiles/runs-nav story). **W5 added the
  browser master-resume upload** — a minimal **Settings** screen (reached from the
  header; a `CONFIGURATION` rail with only *Master resume* live, the other five
  sections disabled until W7) hosts a **Master resume** panel: `GET /api/resume`
  returns the active version plus history, `POST /api/resume` (multipart) parses and
  stores a dropped `.pdf` **or** `.docx` once (a new `DocxResumeParser` joins the PDF
  parser behind a format-sniffing router), and `POST /api/resume/versions/{v}/activate`
  restores an earlier version. The panel shows provenance only (filename, size, parsed
  counts, upload date) — never resume content (ADR-028) — with parse-status and clear
  error feedback. Deferred (E1 stores extracted text + provenance, not the original
  bytes or a note field): downloading the original file and per-version notes. **W6
  added browser document generation** — a job's detail pane now has live **Resume**
  and **Cover letter** chips: `POST /api/jobs/{id}/generate` starts an *asynchronous*
  background task (an LLM call is too slow to block the request) and returns a
  `generation_id`; the chip polls `GET /api/generations/{id}` via React Query until a
  terminal status, then downloads the `.docx` from
  `GET /api/generations/{id}/download` (a plain link — content never enters the DOM,
  ADR-034 §3). The five chip states map onto the run: `empty → pending → ready`
  (with a `needs_review` variant that lists the structural locations to check, never
  the text). A stuck `pending` past `GENERATION_TIMEOUT_SECONDS` self-heals to
  `failed` on the next poll (recovering a task lost to a restart), and a `ready` row
  whose file has vanished returns **410 Gone** so the chip re-generates. This reuses
  Story F's whole synchronous pipeline; W6 added only the async `status` column, the
  API, and the chip. **W7 made the Settings screen fully live** — the `.env`-only
  config is now web-editable and persistent: a `settings` table and a
  `search_profiles` table are seeded from `.env` on first run and authoritative
  thereafter (ADR-031). All five rail sections work: **Voice & tone** (global voice
  descriptor + live preview), **Match threshold** (per-profile, ADR-033), **Run
  schedule** (cron + timezone with a "Next 3 runs" preview), **Search profiles** (full
  CRUD), and **Evaluator provider** (provider/model + the API keys). *(The standalone
  **Match threshold** section was later folded into the Search profiles editor — the
  per-profile threshold now lives on the profile editor rather than its own rail
  section.)* Secrets are
  **write-only** — the API returns only a masked suffix and a server-computed "differs
  from .env" indicator, never a key; a replace persists and a reset reverts to `.env`.
  Runs pick up the DB config through an env bridge that writes effective settings into
  `os.environ` at run start (ADR-035), so edits take effect with no adapter changes.
  **The ADR-032 follow-up then closed the two W7 deferrals:** the web deployment runs
  an in-process `BackgroundScheduler` (`SchedulerManager`) on FastAPI's lifespan
  (`SCHEDULE_ENABLED=true`), so a saved cron reschedules the running job live — no
  restart — and every scheduled fire re-reads settings + profiles from the DB
  (`run_scheduled_cycle`). **Still deferred:** per-profile provider/voice.
  **W8 then added "Run search now":** `POST /api/runs` kicks the same multi-profile
  pipeline a scheduled fire runs, without waiting for cron. It reuses the W6 async
  shape — a `running` `RunRecord` (migration 7) is returned immediately and a FastAPI
  background task executes the pipeline, re-reading settings + profiles from the DB;
  the browser polls the run, then refetches the job list. Only one run executes at a
  time (single-flight → 409); a run with no profiles is a 400; a run lost to a restart
  self-heals to `failed`. The record is summary-only (no job content).
- ~~No database — file output only~~ **Superseded (B1, ADR-023).** A SQLite store
  (`data/agent.db`) now persists jobs and their cross-provider sightings behind
  `JobRepositoryPort`: a seen job is not re-scored, and its stored evaluation is
  reused. CSV and email remain the per-run delivery formats (`OutputPort`), not the
  store. Dedup is exact-match on a normalized fingerprint (ADR-024); the near-miss
  band and per-evaluation threshold are stored per job (ADR-033).
- ~~No application/job-status tracking~~ **Superseded (Story C, ADR-025).** Each
  stored job now carries a nine-state lifecycle (`JobStatus`) and a `saved`
  bookmark, with an append-only `status_history` audit trail. The web Jobs screen
  (`PATCH /api/jobs/{id}/status|saved`) moves a job through the six human-set states;
  transitions are permissive (any → any) but the machine never clobbers a human-set
  status, and a job you have acted on is suppressed from future run reports (still
  sighted).
- ~~No document generation~~ **Superseded (Story F, ADR-029/030).** Document
  generation (the web Jobs screen / `POST /api/jobs/{id}/generate`) turns a stored,
  evaluated job into a **tailored resume** or **cover letter** `.docx` (with
  tone/person/style-notes voice controls). The LLM returns structured JSON; a
  deterministic formatter enforces the hard formatting rules with three outcomes
  (clean / repaired / needs_review) and one corrective retry, never hard-failing to
  nothing and never silently rewriting a number or date. Voice is a structured
  descriptor (ADR-030). Generated content never leaves the server — only the file
  path, provenance, and (for needs_review) structural location hints. Files live at
  `data/generations/{id}.docx` behind `generations` (ADR-034 §3). The async web path
  and download route arrive in W6.
- No user authentication
- No Kubernetes or cloud infrastructure
- No LangGraph orchestration

---

## 12. Implementation Divergences

This section records where the current codebase diverges from the requirements
above. It is a living audit intended to keep the PRD honest; each item is either
a contradiction to reconcile, undocumented behavior to fold into the spec, or a
stale PRD section to refresh.

### 12.1 Contradictions (code does not match the PRD)

| # | PRD requirement | Actual behavior | Location |
|---|---|---|---|
| C1 | "Cache extracted resume text — do not re-parse on every run" (§7, §8) | **Resolved (E1, ADR-028).** The resume is parsed once on upload and cached in SQLite with version history; runs read the active stored version (auto-seeding it from `RESUME_PATH` on a first run) instead of re-parsing the PDF. Manage versions from the web Settings screen (`POST /api/resume`). The legacy per-run parse survives only as a fallback when no resume store is wired. | `ResumeService`, `SQLiteResumeRepository`, `JobSearchService._load_resume` |
| C2 | "Cap results at 50 listings per platform per run" / "No more than 50 results scraped per platform" (§7, §9) | Both scrapers default to `limit=25` and the service never overrides it, so the effective cap is **25/platform**. JSearch additionally fetches up to `JSEARCH_MAX_PAGES` (clamped 1–10 → up to 100 raw results) then discards down to 25, paying for pages it throws away. The number 50 appears nowhere in code. | `LinkedInScraper`, `JSearchScraper`, `JobSearchService` |
| C3 | Default score threshold is `70` (§3, §7) | Real user-facing default is `75` (`SearchProfile.score_threshold` default and env default). The `run()` signature default of 70 is always overridden by profiles. | `SearchProfile` |

### 12.2 Implemented but undocumented (code does more than the PRD)

- **Work-type filtering** — `WORK_TYPE` / `PROFILE_N_WORK_TYPE` (remote/onsite/hybrid)
  is mapped to LinkedIn URL params and JSearch `remote_jobs_only`. Not listed in
  §7 Inputs. Side effect: location auto-resolves to `"United States"` when work
  type is remote-only and no location is supplied.
- **Date-posted filtering** — `DATE_POSTED` / `PROFILE_N_DATE_POSTED`
  (24h / 3days / week / month, default `3days`) applied to both scrapers. Absent
  from the PRD entirely.
- **Rich scoring rubric** — §7 states a result contains only title, company,
  location, URL, score, matched/missing skills, and summary. `MatchResult` also
  carries `seniority_level`, `years_experience_detected`, `hire_recommendation`,
  and a 9-category `score_breakdown` (role alignment, technical stack match,
  system design/architecture, impact & metrics, domain/industry experience,
  problem-space relevance, ownership & leadership, resume signal quality, career
  trajectory). This rubric is undocumented.
- **Broader CLI overrides** — §7 mentions only `--scrapers`. The CLI also
  supports `--query` and `--work-type`.

### 12.3 Stale PRD sections to refresh

- **Project structure (§5)** omits much of the codebase: `anthropic_evaluator.py`,
  the evaluator and scraper factories, `bootstrap.py`, `runner.py`, `scheduler.py`,
  `service_factory.py`, the entire `cli/` and `infra/` packages, and most domain
  models (`SearchProfile`, `RunReport`, `RunCost`, `CostEstimate`, `WorkType`,
  `DatePosted`, `ScraperName`). The diagram lists only Job/Resume/MatchResult.
- **Phase boundaries (§10)** are stale. Phase 2 lists "parallel scraping" and
  "scheduling for automated runs" as future work, but scraping is already
  concurrent (`asyncio.gather` over scrapers) and APScheduler scheduling already
  ships in Phase 1. Only LangGraph remains correctly deferred.
- **Tech stack (§6)** does not list `beautifulsoup4`, `lxml`, `requests`, or
  `pytz` (all in `pyproject.toml`). `beautifulsoup4` / `lxml` appear **unused**
  — LinkedIn scraping uses Playwright selectors, not BeautifulSoup — and are
  candidates for removal.

### 12.4 Minor oversights

- **Empty stub packages** `src/api/`, `src/evaluator/`, `src/scraper/`, and
  `src/tools/` contain only `__init__.py`. `src/evaluator` and `src/scraper` are
  leftover scaffolding (real code lives under `adapters/`); `src/api` is a
  placeholder for the future API entrypoint referenced in runner/bootstrap
  docstrings.
- **"Minimum 2-second delay between requests" (§7)** is enforced only for
  LinkedIn. JSearch issues a single batched request per platform, so no
  inter-request delay applies there.
