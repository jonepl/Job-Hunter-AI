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
- **Update (W1):** implemented — `src/api/` is now the FastAPI driving adapter
  (app factory, `deps.py`, `routers/jobs.py`, `schemas.py`). See ADR-026.

## ADR-022: Gemini pre-filter stage behind a `JobEnrichmentPort`

- **Status:** Accepted
- **Context:** Resume-aware evaluation with OpenAI/Anthropic is the dominant cost
  of a run, and a large share of scraped postings are obviously irrelevant before
  any resume is consulted. A cheap model can discard them — but must never see
  personal data.
- **Decision:** Add a pre-filter stage **between scraping and evaluation**, behind a
  new `JobEnrichmentPort` ABC whose signature accepts only `Job` and never `Resume`
  — the privacy boundary is *structural*, not conventional. The adapter is Gemini
  Flash-Lite via `google-genai`, with strict `response_schema`. Failure is
  **fail-open** (job proceeds to normal evaluation, logged); daily-quota exhaustion
  trips a circuit breaker that skips the stage for the rest of the run.
  Behavior is **skip-but-log**: flagged jobs are never sent to the paid evaluator,
  but every flag and its reason is recorded — nothing disappears silently.
  `ENRICHMENT_MODE=shadow|enforce` (default `shadow`) evaluates everything while
  recording what *would* have been skipped, so the pre-filter's precision can be
  measured before it is trusted.

  **[Refined — v4-grill]** Shadow mode is only useful if its output is a *decision
  surface*, not log noise. Each run report shows Gemini's flagged-to-skip jobs
  compared against the **real scores they received when evaluated anyway** — the
  **false-skip rate** — plus the estimated spend shadow *would* have saved. Without
  that comparison the safe default becomes the permanent state. Graduation to
  `enforce` has a **written criterion**: flip once the false-skip rate is 0 across a
  run of ≥50 evaluated jobs. See `vertical-story-split.md` story A2 and §15.
- **Consequences:** Meaningful cost reduction with no silent loss of postings.
  Resume text cannot reach Gemini — enforced by the port signature and covered by a
  test. Adds a Gemini API dependency and one pipeline stage. Before SQLite exists,
  flags are logged to the run report and log file; once persistence lands they are
  recorded as a `pre_filtered` job status with a reason (see ADR-026's
  machine-never-clobbers-human rule).

## ADR-023: SQLite persistence behind a `JobRepositoryPort`

- **Status:** Accepted (supersedes ADR-007 for *state*; CSV remains a delivery
  format, not a store)
- **Context:** The agent re-scored jobs it had already evaluated on prior runs,
  paying repeatedly for the same LLM call, and had no way to remember that a job
  was dismissed or applied to. Every planned feature — lifecycle tracking, viewing,
  resume storage, document generation, the web UI — needs durable state.
- **Decision:** Introduce SQLite (WAL mode, stdlib `sqlite3`, no ORM) behind a
  `JobRepositoryPort` ABC, with a lightweight migration runner. A single file at
  `data/agent.db`, volume-mounted. Persistence arrives inside the first story that
  needs it (skip re-evaluating seen jobs), carrying only the `jobs` and `sightings`
  tables; later stories extend the schema by exactly what they add.
- **Consequences:** Zero-dependency, zero-network, volume-mountable persistence
  suited to a single-user local tool with no concurrent writers. Postgres would add
  a server, a network hop, and operational surface for no benefit at this scale. The
  core remains ignorant of SQLite — it sees only the port. `OutputPort` (email +
  CSV) is unchanged and still delivers every run.

  **[Refined — v4-grill]** The "no concurrent writers" framing held while the
  scheduler and CLI never ran alongside a web server. Once ADR-032 co-locates the API
  and a `BackgroundScheduler` in **one process**, two writers *can* coincide — a user
  marking a job during a scheduled run. Contention is now **handled explicitly, not
  assumed away** (`PRAGMA busy_timeout`, short per-job commits, all writes through one
  `JobRepositoryPort`). See ADR-034.

## ADR-024: Exact-fingerprint deduplication on a normalized key

- **Status:** Accepted
- **Context:** The same posting appears across LinkedIn, Indeed, Glassdoor and
  ZipRecruiter with inconsistent formatting, and reappears on every scheduled run.
  Identifying "the same job" controls both cost (skip re-evaluation) and dedup
  quality (collapse cross-provider duplicates).
- **Decision:** Identity is `company + title + location`, each canonicalized by
  **pure deterministic normalization** and then matched **exactly**. Normalization
  is not fuzzy matching: it lowercases, strips punctuation and accents, expands a
  curated abbreviation map, strips trailing legal suffixes and known noise tokens,
  and canonicalizes locations — but never makes a similarity judgment, so it cannot
  false-merge. Match = all three canonical fields equal. **Near-miss** (logged,
  never auto-merged) = canonical company and title equal, location differs.
  Distinct = company or title differs. URL and description are excluded from the
  key (URL is a per-sighting attribute; description varies by provider truncation).
  Store both raw fields and the canonical key, plus a `fingerprint_version` integer.
  Fuzzy/edit-distance/embedding similarity, a geographic gazetteer, cross-title
  semantic equivalence, and description-based dedup are explicitly out of scope.
- **Consequences:** The error budget is spent deliberately. A false *split* costs one
  duplicate evaluation — cents, and visible. A false *merge* makes a real job vanish
  before the user ever sees it — the expensive, irreversible error for a job seeker.
  The design therefore biases toward splitting: substantive title qualifiers are
  preserved (`(Backend)` ≠ `(Frontend)`), levels stay distinct
  (`Engineer` ≠ `Engineer III`), and any field that normalizes to empty disables
  dedup for that job rather than merging on a partial key. `fingerprint_version`
  allows rules to evolve without silently mixing key generations. The near-miss log
  is the empirical trigger for adding fuzzy matching later — driven by data, not
  guesswork. Full normalization rules: `vertical-story-split.md` §13.

## ADR-025: Job lifecycle with permissive transitions and append-only history

- **Status:** Accepted
- **Context:** Tracking a job through the application process requires status. A
  strict state machine encodes the intended flow, but real job-hunting is messy —
  you apply to something you never scored, a rejected role reopens, you change your
  mind about a dismissal.
- **Decision:** Nine statuses: `new`, `evaluated`, `pre_filtered` (machine-set) and
  `applied`, `started`, `interviewing`, `offer`, `rejected`, `not_interested`
  (human-set). **Transitions are permissive — any → any** — with an append-only
  `status_history` table as the audit trail. Three guards: (1) reactivating a
  terminal status prompts a **client-side** soft confirm, never a domain rejection;
  (2) setting a status to its current value is an idempotent no-op that writes no
  history row; (3) the single hard **domain** rule — **machine writes never clobber
  a human-set status** (a re-scrape of an `applied` job never resets it to
  `evaluated`). `saved` is a **boolean bookmark, not a status** — a job may be both
  saved and applied.
- **Consequences:** The one user is the authority on their own job hunt; the tool
  does not refuse moves that reality permits. History means a wrong tap costs one
  extra row, not lost data. Strict state machines earn their keep with many users,
  untrusted input, or downstream automation that breaks on illegal states — none
  apply here. Adding a status stays a trivial enum extension rather than a
  transition-matrix redesign.

## ADR-026: FastAPI as a driving adapter, parallel to the CLI

- **Status:** Accepted (activates ADR-021; supersedes the planned static-HTML
  dashboard `OutputPort`)
- **Context:** ADR-021 reserved `src/api/` for a future FastAPI entrypoint, deferred
  until "click-to-act" became a real need. The Job Hunter AI Web design requires
  acting from the browser — marking status, uploading a resume, triggering
  generation — so that need has arrived. An earlier plan to browse jobs via a static
  HTML file emitted as an `OutputPort` adapter cannot serve a React Query SPA, which
  fetches and mutates against an HTTP API.
- **Decision:** Implement `src/api/` as a **driving adapter on the same side of the
  hexagon as the CLI**. Both drive the identical core services and
  `JobRepositoryPort`. Routes contain **no business logic** — they translate HTTP to
  service calls and back. `deps.py` reuses the existing `service_factory`. The
  static-HTML dashboard idea is abandoned; `OutputPort` returns to its real job
  (email + CSV delivery per run) and is no longer a viewing surface.
- **Consequences:** The web UI adds a route + a hook + a screen over services the
  backend stories already built — no logic duplicated, no parallel stack. The CLI
  keeps working unchanged. This is a direct payoff of ADR-001: a second way in cost
  almost nothing. Trade-off: a running process is now required to browse jobs, where
  the static file needed none.

## ADR-027: React 18 + TypeScript + Vite frontend with React Query

- **Status:** Accepted
- **Context:** "Job Hunter AI Web" needs a real client. A prior project ("Rental
  Buddy") established a working stack, and reusing it avoids relitigating settled
  tooling choices.
- **Decision:** React 18 + TypeScript + Vite, TailwindCSS for styling, React Query
  v5 for all server state, Jest + React Testing Library for unit/integration tests,
  Playwright for E2E. A **typed API client** in `web/src/api/` is the single seam
  between frontend and backend — the only place `fetch` is called, with types
  derived from the Pydantic response models so the two cannot drift. Tailwind's
  `theme.extend` is generated from the existing `tokens.css`; no hardcoded colors.
- **Consequences:** Familiar, well-supported tooling with a fast dev loop. React
  Query removes hand-rolled caching, loading, and invalidation logic. The typed
  client localizes breakage when the API changes. Adds a Node build step to a
  previously Python-only repo (see ADR-032).

## ADR-028: Resume stored once, provenance-only, with version history

- **Status:** Accepted — **implemented by E1** (resolves the `docs/prd.md` §12
  divergence C1). E1 ships the parse-once cache, `resumes` version-history table
  (migration 3), `ResumeService`, the `resume` CLI, and the corpus-aware evaluator
  line (gap 8b). Deferred to F: full structured-section extraction (experience /
  education entries) — E1 caches the raw-text corpus plus provenance and
  best-effort skill/role counts only.
- **Context:** The resume PDF was re-opened and re-parsed on every `run()` — once per
  profile and again on every scheduled trigger — despite the PRD promising a cache.
  Document tailoring additionally needs a richer representation than a raw text blob.
- **Decision:** Parse the resume once on upload and persist it, enriching the
  existing `Resume` entity **in place** (same type, richer fields) rather than
  introducing a new entity — so `ResumeTailorPort.tailor()` can accept `Resume` and
  benefit from the enrichment without an interface change. Runs read the stored
  representation. Keep a **version history** with restore. The API and UI expose
  **provenance only** — filename, version, upload timestamp, size, parsed counts
  (skills, roles), and a readiness state — and **never render resume content**.

  **[Clarified — v4-grill]** The master resume is a **single comprehensive corpus** —
  everything the candidate has done — applied to *all* search profiles. There is **no
  per-profile resume** in v1 (no reserved `profile_id` seam). Because tailoring
  (ADR-029) *selects* from this superset rather than adding to it, the "never add
  experience not in the original" rule is satisfied structurally. One consequence for
  evaluation: since the corpus is broader than any single targeted resume, the
  evaluator prompt is **instructed to score the candidate's *relevant* experience for
  each role and not penalize breadth as scattered trajectory** — otherwise the
  `career trajectory` and `resume signal quality` categories would understate fit.
- **Consequences:** Eliminates redundant parsing on every run. Structured sections
  make the tailoring rules ("preserve specific numbers", "never add experience not
  in the original") mechanically checkable rather than merely prompted. Fabrication
  detection is deliberately weak until this lands, and strengthens once it does.

## ADR-029: Document generation ports with a three-outcome formatter

- **Status:** Accepted — implemented by Story F (the `generate` CLI) and **W6** (the
  async web path: the `generations.status` column, `POST /generate` +
  background task, the `GET /generations/{id}` poll, and the download route with the
  410-Gone fallback). The sibling `ResumeTailorPort` /
  `CoverLetterPort`, the deterministic `document_formatter`, the consolidated
  `DocxWriterPort` (one writer for both artifacts, replacing the separately-named
  `TailoredResumeWriterPort` now F1+F2 are merged), and the `generations` table all
  landed in F.
- **Context:** Tailored resumes and cover letters must obey hard formatting rules
  (no semicolons, `•` bullets only, em-dashes banned, hyphens only inside compound
  words) that an LLM will not perfectly honor. A deterministic post-processor must
  enforce them. The question is what it does on a violation.
- **Decision:** Sibling narrow ports — `ResumeTailorPort` and `CoverLetterPort`
  (not one generic `DocumentGenerationPort`; the two have genuinely different
  validation rules) — plus a `TailoredResumeWriterPort` for `.docx` rendering, since
  `OutputPort`'s contract (`deliver(results)`) is the wrong shape for a
  user-triggered single artifact. Both generation ports hard-allowlist
  `openai|anthropic` and fail at startup otherwise. The LLM returns **structured
  JSON**, not a text blob, so section order is a property of the renderer.

  The post-processor classifies violations and produces **three outcomes**:
  1. **clean** — no violations; ship.
  2. **repaired** — only *mechanical* violations (unambiguous character fixes:
     em-dash → comma/period, semicolon → period, `-` bullet → `•`); fixed
     deterministically, shipped **with a repair note** recorded on the generation.
  3. **needs_review** — a *semantic-adjacent* violation the processor will not
     safely auto-fix. The hyphen rule is the trap: `full-stack` (keep) versus
     `2020-2024` or `Python - 5 years` (fix) is not a purely mechanical distinction,
     and a blind repair could silently alter a date or a number. The `.docx` is
     **still written**, the generation is marked `needs_review`, and the ambiguous
     locations are recorded.

  Before flagging, **exactly one** corrective retry feeds the violations back to the
  model. Capped at one so a stubborn model cannot burn unbounded spend.

  Generation is **asynchronous**: an LLM call is too slow to block an HTTP request.
  `POST` returns a `generation_id`; the client polls the `generations` row until a
  terminal status. A stuck `pending` times out to `failed`. Server-Sent Events were
  rejected — their benefit is streaming text to the screen, and document content is
  never rendered.
- **Consequences:** A generation is never lost to a formatting nit, and numbers,
  dates, and proper nouns are never silently rewritten. The user always knows when
  output was touched or needs their eyes. Content never reaches stdout, logs, email,
  or the DOM — only a file path and, for `needs_review`, the *locations* to check.
  The three outcomes map directly onto the UI's generation-chip states.

## ADR-030: Voice and tone as a structured descriptor, not writing samples

- **Status:** Accepted (supersedes an earlier samples-primary proposal) —
  implemented by Story F as the `VoiceDescriptor` entity (tone / first-person toggle
  / style notes), fed to `CoverLetterPort`. Persistence in the `settings` table and
  the live-preview tuning loop follow in W7.
- **Context:** Generated cover letters should sound like the candidate. Two
  mechanisms were considered: few-shot **writing samples** (high fidelity, captures
  rhythm and vocabulary) versus an explicit **descriptor** (easy to configure, but
  adjectives underspecify voice). The initial lean was samples-primary.
- **Decision:** **Descriptor-only.** Voice is a tone preset
  (`direct`/`warm`/`formal`/`bold`), a first-person toggle
  (`first_person`/`implied`), and free-text **style notes** — e.g. *"Keep sentences
  short. Lead with measurable outcomes. Never use 'passionate', 'synergy',
  'rockstar'."* A live **preview** is the tuning loop. Writing samples are dropped.
- **Consequences:** Style notes are *instructions*, which a model follows more
  reliably than it reverse-engineers rules from pasted prose — the user writes the
  rules directly instead of making the model infer them. The preview closes the loop
  faster than curating samples would. Crucially, this **removes a privacy
  exception**: samples would have had to be stored as raw personal text under the
  provider allowlist, whereas style notes are configuration. The provenance-only
  storage rule (ADR-028) stays unbroken. If fidelity ever proves insufficient, one
  optional sample field is a cheap later addition — the preview will reveal the need.

## ADR-031: Settings persistence — DB for preferences, write-only secrets

- **Status:** Accepted — implemented by **W7** (the `settings` + `search_profiles`
  tables, `SettingsService`, `GET/PUT /api/settings`, `PUT/DELETE
  /api/settings/secrets/{name}`, profile CRUD, and the browser Settings screen). The
  two parts deferred at W7 — the in-process scheduler on FastAPI lifespan + live cron
  reschedule, and per-run DB re-reads — **landed in the ADR-032 follow-up**:
  `run_scheduled_cycle` re-reads settings + profiles from the DB on every scheduled
  fire, and a cron edit reschedules the running `BackgroundScheduler` live. One
  amendment: secrets are **editable and persisted in
  the DB**, seeded from `.env`, with a server-computed **"differs from .env"** flag —
  not `.env`-only. The API still never returns a full secret (masked suffix +
  configured/overridden flags only).
- **Context:** All configuration lived in `.env`, read at process start. A web
  Settings screen requires a writable store, and a rule for how a running scheduler
  picks up changes. Secrets need different handling from preferences.
- **Decision:** `.env` is the **bootstrap seed**; a `settings` table in the existing
  SQLite is the **runtime preferences** layer, seeded from `.env` on first run (no
  empty-state cliff) and authoritative thereafter. Web-editable: search profiles,
  cron expression, evaluator provider and model, score threshold, top results,
  active scrapers, date filter, voice descriptor, `ENRICHMENT_MODE`. **Each
  scheduled run reads settings from the DB at run start**, so edits go live on the
  next run without a restart.

  **Secrets are write-only, not `.env`-only.** The API never returns a full secret
  value; it may return a **masked suffix** (`sk-ant-••••4Kq2`) for recognition and
  accept a **replacement** write. The changing cron expression is the one setting
  that cannot be handled by per-run reads — it is resolved by ADR-032.
- **Consequences:** The real constraint (no secret exfiltration to the browser) is
  satisfied without forcing the user to leave the app, edit a file, and restart —
  a poor trade for a localhost tool. Two configuration sources exist, but with a
  clean rule: `.env` seeds and holds secrets; the DB holds preferences. Anything
  read once at boot must be re-read per run or explicitly rescheduled.

## ADR-032: Multi-stage single container with an in-process scheduler

- **Status:** Accepted — **implemented**. The multi-stage Docker build and same-origin
  SPA serving landed with the web stories (the `node` build stage in `Dockerfile`,
  FastAPI's `StaticFiles` mount at `/`). The in-process scheduler landed as a
  follow-up after W7: `SchedulerManager` (a `BackgroundScheduler`) starts on FastAPI's
  `lifespan` when `SCHEDULE_ENABLED=true`, and a cron/timezone edit in the Settings
  screen reschedules it by a direct `reschedule_job` call (`PUT /api/settings`). Each
  fire re-reads settings + profiles from the DB (`run_scheduled_cycle`), closing the
  two W7 deferrals (live cron reschedule + per-run DB re-reads). The standalone
  `BlockingScheduler` (`start_scheduler`) remains for the CLI `python -m src.main`
  scheduled mode, which never boots the web server and cannot be rescheduled live.
  (Extends ADR-008 and revises ADR-018.)
- **Context:** ADR-008 ships one all-in-one container. Adding a React frontend
  introduces a Node build step, and the web server must coexist with APScheduler.
  ADR-018 used a `BlockingScheduler`, which cannot share a process with uvicorn.
- **Decision:** A **multi-stage Docker build**: a `node` stage builds `web/` to
  static assets, which are copied into the Python image. FastAPI serves the SPA at
  `/` and the API under `/api` — **one container, one port, same origin** (which
  also removes production CORS entirely). Development still uses the Vite dev server
  proxying to FastAPI.

  The container runs **one process**: uvicorn in the foreground, with APScheduler as
  a **`BackgroundScheduler`** (replacing `BlockingScheduler`) started on FastAPI's
  lifespan startup, gated by `SCHEDULE_ENABLED=true`. CLI immediate mode remains a
  separate invocation that never boots the server.
- **Consequences:** Because the API and the scheduler now share a process, editing
  the cron expression in the web UI **reschedules the APScheduler job by a direct
  method call** — no cross-process signaling, no DB polling, no container restart.
  This resolves the hardest sub-question in ADR-031. A single-user localhost tool
  gains nothing from service separation or independent scaling, so unifying is
  strictly simpler. Trade-off: the frontend build is now part of the backend image,
  and a scheduler crash shares a process with the web server. The bind/publish and
  write-contention consequences of running one process are addressed in **ADR-034**.

## ADR-033: Near-miss as a fixed band; evaluation threshold stored per job

- **Status:** Accepted (refines ADR-012; resolves the open decision flagged in
  `.claude/rules/design.md` and `docs/design/ui-spec.md` §5.1)
- **Context:** The UI's signature `<ThresholdRail>` colors every score in three
  states — qualify / near-miss / below — and the Match-threshold settings screen shows
  a "near-miss band." But the backend had no such concept: near-miss existed **only**
  in the zero-results case (top-5 below threshold), and `RunReport.suggested_threshold`
  floored the lowest of those five to the nearest 5 — a run-relative artifact, not a
  band. On a normal run every non-qualifying job was simply "below," so the design's
  amber band had nothing to compute from. Separately, the score threshold is
  **per-profile** (`SearchProfile.score_threshold`, ADR-019), yet the UI treated it as
  one global value, and `TRACKED` deliberately mixes jobs from profiles with different
  thresholds.
- **Decision:** (1) The near-miss band is a **fixed-width offset below the active
  threshold**, owned by the backend as `NEAR_MISS_BAND` (default `15`, matching the
  design's 60–74 at threshold 75). `near_miss_floor = threshold − NEAR_MISS_BAND`; a
  job is *near-miss* when `near_miss_floor ≤ score < threshold`, *qualify* when
  `score ≥ threshold`, *below* otherwise. This single rule feeds the rail, the email
  near-miss cards, the CSV, and the zero-results suggested threshold — **retiring** the
  old floor-the-lowest-of-five rule. (2) The threshold used to evaluate a job is
  **persisted on the evaluation row** and the API returns it per job. `<ThresholdRail>`
  always reads the job's own stored `threshold` and derived `nearMissFloor`; there is
  **no global threshold**. The header threshold is a per-profile display, shown as
  mixed/"—" in the cross-profile `TRACKED` view. The Match-threshold settings screen
  edits the *selected profile's* threshold.
- **Consequences:** The three-state rail is truthful on every run, not only
  zero-result runs, and cards from different profiles color correctly in one list.
  Near-miss becomes a first-class, absolute concept shared by every output surface. The
  legacy bare `SCORE_THRESHOLD` env var (single-search fallback) is left untouched —
  removing it is the separate legacy-config cleanup tracked in `remaining_work.md`.
  Lands in the B1 story (persistence) and is consumed by W1 (`<ThresholdRail>`).

## ADR-034: Deployment hardening for the single-process web server

- **Status:** Accepted (addresses consequences of ADR-032 left open there; refines
  ADR-023 and ADR-029)
- **Context:** ADR-032 runs uvicorn and a `BackgroundScheduler` in **one process**,
  serving a **single SQLite file**, inside Docker, on `localhost` with no auth, and the
  document-generation feature writes `.docx` files to disk. Three operational gaps
  followed that no prior ADR closed: concurrent writers, container binding, and
  generated-file lifecycle.
- **Decision:**
  1. **SQLite write contention.** A scheduled run (long, write-heavy) can now coincide
     with a user write from the browser (mark status, save, generate). SQLite permits
     one writer at a time; WAL does not change that. Handle it explicitly: set
     `PRAGMA busy_timeout` (~5000 ms) on every connection, keep the run's writes in
     **short per-job commits** rather than one run-long transaction, and route all
     writes through the single `JobRepositoryPort` instance. Amends ADR-023's "no
     concurrent writers" line to "contention handled, not assumed away."
  2. **Container binding.** Bind uvicorn to `0.0.0.0` **inside** the container (so port
     forwarding works) but **publish on host loopback only** — `127.0.0.1:8000:8000` in
     `docker-compose.yml`, never `8000:8000`. This keeps the "loopback-only, therefore
     no auth" model honest. A warning comment sits at that compose line; the explicit
     trigger is: **any non-loopback publish makes auth mandatory.**
  3. **Generated-file storage.** Tailored `.docx` files live at
     `data/generations/{generation_id}.docx`, under the same volume as `data/agent.db`
     (file and the `generations` row that references it share a lifecycle and mount).
     Filenames are opaque ids — no candidate name or job title in the path.
     `GET /download` checks the file exists before streaming and returns **410 Gone**
     if a `ready` row's file is missing, so the chip falls back to regenerate rather
     than error. Retention: **keep everything, user-deletable** (row + file); no
     time-based auto-purge at single-user scale.
- **Consequences:** The single-process web deployment is safe to use as the product
  intends — browsing and acting while a scheduled run writes. Costs a few explicit
  rules in B1 (contention), W1 (binding), and F/W6 (file storage) instead of silent
  assumptions. If the app ever leaves localhost, the binding trigger forces the auth
  decision rather than leaving it implicit.

## ADR-035: Settings applied to the environment (the env bridge)

- **Status:** Accepted (implements part of ADR-031, added in W7)
- **Context:** ADR-031 moves operational config from `.env` into a DB `settings`
  table. But every existing factory and adapter already reads its config from
  `os.getenv` — `EVALUATOR_PROVIDER`, `EVALUATOR_MODEL`, `*_API_KEY`,
  `ENRICHMENT_MODE`, `GEMINI_MODEL`, `SCHEDULE_CRON`, cost rates, and more. Making DB
  edits take effect could mean threading a settings object through every one of those
  constructors — a wide, invasive refactor for a single-user tool.
- **Decision:** Bridge, don't rewire. `SettingsService.apply_to_environment()` writes
  the effective DB settings (and any secret overrides) **back into `os.environ`** at
  the run entrypoint (`src/main.py`, before CLI overrides), so the unchanged factories
  read the current configuration transparently. Precedence is **`.env` → DB → CLI**:
  `.env` seeds and is the fallback, the DB overrides it, and a CLI flag (testing only)
  overrides both because it is applied last. **Search profiles are the exception** —
  they are read directly from the DB (`ProfileRepository`), never bridged through the
  environment, since they are structured records, not scalar env vars. Secrets are
  seeded lazily: the `.env` value stays the default and is only copied into the DB
  when the user explicitly replaces it (so keys are not duplicated into SQLite
  unnecessarily).
- **Consequences:** DB-backed settings take effect with **zero changes** to the
  evaluator, enrichment, scheduler, and cost factories. The cost is one `os.environ`
  mutation per run — contained, reversible, and easy to reason about. Because the
  bridge runs at the entrypoint (not per adapter build), settings are read **once at
  run start**; per-run re-reads inside a long-lived scheduler process arrive with the
  in-process scheduler (ADR-032). If a future entrypoint (an API-triggered run, W8)
  needs current settings, it calls `apply_to_environment()` itself.

## ADR-036: Web-triggered runs as an async, single-flight, summary-only record

- **Status:** Accepted — implemented (W8)
- **Context:** Until now a run started only from cron (the in-process scheduler,
  ADR-032) or the CLI. The browser needed a "Run search now" button, but a full run
  (scrape → optional pre-filter → evaluate → deliver) takes minutes — far too long to
  block an HTTP request — and it writes to the same single SQLite file every other
  path writes to (ADR-034 §1). Two runs at once would contend for that one writer and
  double the API spend for no benefit.
- **Decision:** Reuse the W6 async generation shape (ADR-029) rather than invent a new
  one. `POST /api/runs` validates preconditions synchronously, creates a `running`
  `RunRecord` (migration 7), and returns it immediately (202); a FastAPI
  `BackgroundTask` runs `RunService.execute_run`, which calls
  `apply_to_environment()` (ADR-035) + re-reads profiles from the DB (ADR-031) and runs
  exactly what a scheduled fire runs (`run_all_profiles`). The client polls
  `GET /api/runs/{id}` until a terminal status, then refetches the job list.
  **Single-flight:** at most one row is ever `running`; a second `POST` is a **409**,
  enforced by `RunService` (not a DB constraint) so the message can name the active
  run. A run with no profiles is a **400**. **Self-healing:** a `running` row older than
  `RUN_TIMEOUT_SECONDS` flips to `failed` on read, so a task lost to a restart recovers
  and frees the guard. The record is **summary-only** — profiles run, jobs found, newly
  evaluated, qualifying — plus a bare exception *type name* on failure; no job content
  or raw error message is ever stored or returned (CLAUDE.md #2). Evaluated jobs land in
  the `jobs` table as always; the run row is just the lifecycle handle.
- **Consequences:** The button is a thin, honest wrapper over the exact scheduled
  pipeline — no divergent "web run" code path to keep in sync. The `trigger` column is
  future-proofed so the scheduled and CLI paths could record their runs in the same
  table later. Single-flight is a policy in the service, so relaxing it (e.g. a queue)
  is a local change. The cost: a run cannot be cancelled mid-flight today — it runs to
  completion or times out; and because the summary is intentionally lean, the run row is
  not a substitute for the emailed/CSV `RunReport`, which remains the full delivery.

## ADR-037: Persist theme in localStorage; put navigation state in the URL

- **Status:** Accepted (added post-W7)
- **Context:** Reloading the browser reset two things a user expects to survive: the
  active theme (light/dark) and the page they were on (Search vs Settings, the active
  Settings section, the Search rail selection). Both were React `useState` only — the
  theme reset by explicit design (the "no browser storage" rule in `design.md`), and
  the screen reset because there was no router (`App.tsx` held a `view` `useState`).
  The two problems have different correct homes, and conflating them (e.g. persisting
  the page in `localStorage`) would be an anti-pattern.
- **Decision:**
  1. **Theme → `localStorage`** (key `theme`), the single, narrow carve-out to the
     no-browser-storage rule. A synchronous guard in `index.html` resolves and stamps
     `<html data-theme>` *before first paint* (stored choice → `prefers-color-scheme`
     → light), eliminating the flash of wrong theme; `theme.tsx` then keeps React
     state in sync. An explicit toggle **pins** the choice; with no stored choice the
     app follows the OS live.
  2. **Navigation → the URL**, via TanStack Router (chosen to pair with the existing
     `@tanstack/react-query`). `/` is Search (`?view=tracked` / `?profile=<id>` encode
     the rail selection as validated search params); `/settings/<section>` is Settings.
     `searchView.tsx` keeps its public API (`useSearchView` / `useResolvedSelection` /
     `useViewedProfile`) but reads/writes the URL instead of context state, so the rail,
     top bar, and results column were untouched. A stale `profile` id or unknown
     `section` in the URL falls back to the default rather than erroring.
- **Consequences:** Refresh, back/forward, deep links, and multi-tab all behave
  correctly for the page — properties `localStorage`-for-page would have broken. The
  former `App.tsx` shell became the router's `RootLayout` (`router.tsx`). Selected job
  id and job filters remain ephemeral local state by choice (not deep-linked today).
  `@tanstack/react-router` was pinned to `1.170.18` — explicitly past the `1.169.5–8`
  malicious builds of the 2026-05-11 supply-chain incident (CVE-2026-45321). Tests gained
  a `renderWithRouter` helper (memory history) and a `TextEncoder`/`scrollTo` polyfill in
  the jsdom setup, both required by the router core.
