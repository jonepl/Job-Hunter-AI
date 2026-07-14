> # ⚠️ SUPERSEDED — do not implement from this document
>
> This is an **early, CLI-only draft** that predates the web pivot and the final
> decision set. Its ADR numbers (§11) collide with the real log, and several of its
> mechanisms are the exact ones the settled plan **explicitly rejected**. Kept only
> as historical record of the reasoning.
>
> **Authoritative sources instead:**
> - Decisions → `docs/adr.md` (ADR-022…034)
> - Stories, sequence, fingerprint spec, grill resolutions → `docs/build/vertical-story-split.md`
> - UI/screen/component contract → `docs/design/ui-spec.md`
>
> **Known contradictions with the settled plan (non-exhaustive):**
> - **No UI** here vs. a React SPA + FastAPI (ADR-026/027).
> - **7 statuses + strict transition matrix** vs. **9 statuses, permissive any→any** (ADR-025).
> - **Hashed `sha1` fingerprint** vs. **indexed human-readable TEXT** (ADR-024).
> - **Similarity/"cheap ratio" near-miss** vs. **exact canonical match, never a similarity
>   judgment** (ADR-024) — and near-miss *display band* is now `NEAR_MISS_BAND` (ADR-033).
> - **Writing-sample voice** (`VOICE_SAMPLES_DIR`) vs. **descriptor-only, no samples** (ADR-030).
> - **`REEVALUATE_AFTER_DAYS` time window** vs. skip-on-fingerprint-match / reuse stored score (B1).
> - **`output/tailored`** vs. **`data/generations/{id}.docx`** (ADR-034).
> - This doc's **§11 ADR-022…026** describe *different decisions* than the real ADR-022…026.

---

# Design Spec — Persistence, Dedup, Job Tracking, and Document Generation

**Status:** ⚠️ SUPERSEDED (see banner above) — was: Draft for implementation
**Scope:** Adds durable state (SQLite) and four user-facing features to the Job Search Automation Agent — cross-provider dedup, a job lifecycle tracker, tailored-resume generation, and cover-letter generation — without violating Hexagonal Architecture (core never imports adapters).

This spec assumes the architecture settled over the prior design conversation. Where a decision was made on your behalf it is marked **[DEFAULT — change if wrong]**. Where a decision remains genuinely yours it is marked **[YOUR CALL]**.

---

## 1. Decisions locked in

Three product decisions were confirmed and drive the schema:

1. **Dedup: exact fingerprint only.** No fuzzy matching in v1. Near-misses are logged for later tuning rather than auto-merged. Rationale: a wrong merge hides a real job permanently, which is worse than a duplicate slipping through.
2. **Job status: full application tracker with history.** Not a single suppression flag. States extend through the application lifecycle and every transition is recorded with a timestamp.
3. **Re-evaluation: time-based, append history.** When a known job reappears, it is re-evaluated only if the last evaluation is older than `REEVALUATE_AFTER_DAYS`. Evaluations are appended, never overwritten, so score history survives.

Consequence of (2): the model needs a `status_history` table and a legal-transition rule set, not just a column. Consequence of (3): evaluations are a first-class table keyed by job and timestamp, and each evaluation stores a description hash so a content-triggered re-eval mode can be switched on later with no migration.

---

## 2. Domain model

All entities are Pydantic models (ADR-002). The current `Job` entity effectively becomes `JobSighting`; identity moves up to `CanonicalJob`.

### CanonicalJob — the position
The deduplicated job. One per real-world opening, regardless of how many platforms surfaced it.

```
CanonicalJob:
    id: str                      # short surrogate, stable for life (see §4 note)
    fingerprint: str             # exact-match key (see §3)
    company: str
    title: str
    normalized_title: str
    location: str
    description: str             # full JD text — survives the run
    description_hash: str        # sha1 of description; enables future content-triggered re-eval
    status: JobStatus            # denormalized current state (fast queries)
    first_seen: datetime
    last_seen: datetime
    status_changed_at: datetime
```

### JobSighting — an observation
One row each time a platform surfaces a canonical job.

```
JobSighting:
    id: str
    canonical_job_id: str        # FK
    platform: str                # linkedin | indeed | glassdoor | ziprecruiter
    url: str
    scraped_at: datetime
```

### JobStatus — the state machine
```
new           # seen, not yet evaluated
evaluated     # scored by the LLM
applied       # user applied
interviewing  # user in process
rejected      # closed unsuccessful
offer         # offer received
not_interested # user dismissed
```

**Legal transitions** (validated in a core domain service, not the DB):

- `new → evaluated` (automatic, in-pipeline)
- `new → not_interested`, `evaluated → not_interested`
- `evaluated → applied` (and `new → applied` if the user applies before a score exists)
- `applied → interviewing`, `applied → rejected`
- `interviewing → offer`, `interviewing → rejected`
- `not_interested → new` (undismiss — allow it; cheap and occasionally wanted)

Anything else raises a domain error surfaced by the `mark` command as a clear message.

**Suppression rule:** a canonical job whose status is **not** in `{new, evaluated}` is excluded from evaluation and from RunReport surfacing on future runs. So once you apply, dismiss, or reach any terminal state, the job stops re-appearing in your email. It remains visible via the `jobs` command.

### StatusTransition — the history log
```
StatusTransition:
    id: str
    canonical_job_id: str        # FK
    from_status: JobStatus | None  # None on first insert (creation)
    to_status: JobStatus
    changed_at: datetime
    note: str | None             # optional free text from `mark --note`
```

### Evaluation — appended per scoring
Carries the full `MatchResult` rubric (which is richer than the PRD implies — CLAUDE.md confirms `seniority_level`, `years_experience_detected`, `hire_recommendation`, and the 9-category `score_breakdown`).

```
Evaluation:
    id: str
    canonical_job_id: str        # FK
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str
    seniority_level: str
    years_experience_detected: int
    hire_recommendation: str
    score_breakdown: dict         # 9 categories
    description_hash: str          # JD hash at eval time (for future content-trigger)
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    evaluated_at: datetime
```

### GenerationRecord — provenance for generated documents **[DEFAULT — provenance only]**
The `.docx` on disk is the source of truth. The DB stores *that a document was generated*, not its content. This keeps the DB lean and consistent with "the artifact is the interface." Switch to storing content only if you later want regenerate-exactly or in-app browsing.

```
GenerationRecord:
    id: str
    canonical_job_id: str        # FK
    doc_type: str                # tailored_resume | cover_letter
    output_path: str
    placeholders: list[str]      # unresolved [PLACEHOLDER] markers emitted
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    generated_at: datetime
```

### TailoredResume / CoverLetter — structured generation outputs
Structured (not text blobs) so the `.docx` renderer lays out sections deterministically and the formatting validator checks per-line.

```
TailoredResume:
    canonical_job_id: str
    job_title: str
    company: str
    summary: str
    experience: list[ExperienceEntry]
    projects: list[ProjectEntry]      # empty = omit the section
    skills: list[str]
    education: list[EducationEntry]
    placeholders: list[str]
    provider: str
    model: str
    generated_at: datetime
```

`CoverLetter` is a sibling shape (salutation, body paragraphs, closing, placeholders, provenance). Its formatting rules overlap the resume's but its structure differs — see §6 on why these are sibling ports.

---

## 3. Dedup / fingerprint

**Fingerprint = `sha1(normalized_company + "|" + normalized_title + "|" + normalized_location)`**, exact match only.

Normalization (in `core/services/job_identity.py`, a domain rule):
- lowercase, collapse whitespace, strip surrounding punctuation
- company: strip legal suffixes (`inc`, `llc`, `ltd`, `corp`, `co`)
- title: expand common abbreviations (`sr` → `senior`, `jr` → `junior`), strip seniority-noise only if you choose to — **[DEFAULT — expand abbreviations, keep seniority words]** so "Senior SWE" and "SWE" stay distinct (they're different roles)
- location: normalize remote spellings (`remote - us`, `remote (us)` → `remote us`)

**Near-miss logging:** when a new job's fingerprint doesn't match but its normalized company+title are *close* (cheap ratio check), write a row to `near_miss_log` (or a log line) so you can review whether fuzzy matching would help before enabling it. This is observation only — it never merges.

The dedup step resolves each sighting: compute fingerprint → `find_by_fingerprint` → if found, add a sighting and update `last_seen`; if not, create the canonical job (status `new`) and add the first sighting.

---

## 4. Persistence — SQLite behind a port

**One store:** `data/agent.db`, volume-mounted alongside `output/` and `logs/`. Stdlib `sqlite3`, no ORM, WAL mode + a busy timeout for the scheduler-writes / command-reads pattern. Hand-written SQL confined to a single adapter so a future Postgres port is a one-file rewrite.

**Port:** `JobRepositoryPort` (ABC, ADR-003) in `core/ports/`; `SqliteJobRepository` in `adapters/persistence/`. The port trades in **Pydantic entities, never rows.**

Method surface:
```
find_by_fingerprint(fingerprint) -> CanonicalJob | None
get(job_id) -> CanonicalJob | None
resolve_or_create(job_data) -> CanonicalJob        # dedup entry point
add_sighting(canonical_job_id, sighting) -> None
set_status(job_id, to_status, note=None) -> None    # column + history row, one tx
list_by_status(statuses) -> list[CanonicalJob]
record_evaluation(canonical_job_id, evaluation) -> None
latest_evaluation(job_id) -> Evaluation | None
record_generation(canonical_job_id, record) -> None
log_near_miss(a, b, similarity) -> None             # optional
```

**Schema (tables):** `schema_version`, `canonical_jobs`, `job_sightings`, `status_history`, `evaluations`, `generations`, `near_miss_log`. JSON-typed columns (`matched_skills`, `score_breakdown`, etc.) stored as TEXT via `json.dumps`, parsed back into entities in the adapter.

**Job id — [DEFAULT — short random surrogate, not derived from fingerprint].** `id` is a short random token (e.g. 6-char base32, typeable as `tailor --job-id 7f3a9c`) generated once at creation and stable forever. `fingerprint` is a separate UNIQUE column. This decouples the id from the normalization algorithm — if you tweak normalization later, fingerprints can be recomputed without breaking any `--job-id` reference or FK. (Deriving the id from the fingerprint would be more "elegant" but makes ids brittle to normalization changes.)

**Migrations — [DEFAULT — versioned functions].** A `schema_version` table plus an ordered list of migration functions in the adapter, run on startup. Sufficient at this scale; no migration framework.

**Backfill — [DEFAULT — start empty].** No backfill from historical CSVs (they're display-oriented and fragile to parse — the exact coupling we rejected). The DB populates from the next run forward. Cost: dedup has no history for the first run or two.

---

## 5. Pipeline changes

`JobSearchService` gains a `JobRepositoryPort` dependency (constructor injection, like its other ports). Two cheap filter steps slot between scrape and evaluate; nothing else in the pipeline changes.

```
scrape
  → resolve sightings to canonical jobs (dedup, exact fingerprint)   [NEW]
  → drop jobs whose status ∉ {new, evaluated}  (suppression)          [NEW]
  → drop jobs evaluated within REEVALUATE_AFTER_DAYS (skip re-eval)   [NEW]
  → evaluate remainder → record_evaluation + set status `evaluated`   [writes through repo]
  → sort / filter / rank                                              (unchanged)
  → build RunReport                                                   (unchanged)
  → deliver (email + CSV)                                             (unchanged)
```

The skip-already-evaluated step is the one that saves real LLM spend on repeat postings — it's a cost feature, not just cosmetic dedup.

---

## 6. Generation features — sibling ports

**[YOUR CALL — still recommend siblings]** Two narrow ports rather than one generic `DocumentGenerationPort`:

- `ResumeTailorPort.tailor(resume, canonical_job, work_types) -> tuple[TailoredResume, int, int]`
- `CoverLetterPort.generate(resume, canonical_job, voice_profile) -> tuple[CoverLetter, int, int]`

Both return the `(entity, input_tokens, output_tokens)` tuple matching the ADR-016 evaluator convention, so cost tracking reuses `EvaluationCost` and the existing per-provider rate machinery unchanged.

Why siblings, not one generic port: the two documents have genuinely different structure and different validation rules (the resume's full formatting hard-rule set doesn't all map onto a cover letter). Generic document ports get mushy. They **share adapter internals** — client setup, retry, token extraction, JSON parsing — factored into helpers also used by the evaluator adapters. Share code, not contracts.

**Provider allowlist (structural privacy constraint).** Both generation factories hard-allowlist `openai | anthropic` and **fail at startup** on anything else. This is the mechanism that prevents resume content from ever routing to Gemini's free tier (which trains on submitted data). The "why" lives in a code comment and in `docs/env.md` so the constraint survives being forgotten.

**Output:** a `TailoredResumeWriterPort` (and `CoverLetterWriterPort`) with a `python-docx` adapter in `adapters/output/`, writing to `TAILOR_OUTPUT_DIR` / `COVERLETTER_OUTPUT_DIR`. **Content is never printed to chat, stdout, logs, or email — only the output path is logged.** This is structural: the service hands the entity to the writer port and nothing else ever touches it.

**JD source at generation time:** the stored `description` on the `CanonicalJob`, never a re-fetch. The command warns when `last_seen` is older than a threshold (staleness), with an optional future `--refresh` flag.

**Resume dependency to track:** `ResumeTailorPort` accepts the `Resume` *entity*, not a raw string. Today `Resume` is `raw_text` + timestamp, so fabrication-detection validation (§7) is weak in v1. When the separate resume-storage-improvement feature enriches `Resume` with structured sections **in place (same type, richer fields)**, tailoring quality and validation improve with no interface change. **If that feature instead introduces a new entity or changes resume loading, this port signature is the coupling point to revisit** — worth a one-line note in that feature's plan.

**Voice/tone for cover letters — [YOUR CALL / needs its own brainstorm].** `voice_profile` input is under-specified. Proposal: reference writing samples live as files in a mounted `VOICE_SAMPLES_DIR` (user-editable, not DB), and the port reads and feeds them to the prompt. "User's voice from samples" has real failure modes (pastiche, over-imitation) and deserves a dedicated design pass before build. Flagged, not solved here.

---

## 7. Formatting post-processor (deterministic, core-side)

The LLM will not reliably obey the formatting hard rules, so a deterministic validator in the core enforces them on the generated entity **before** the writer port is invoked. Runs on both resume and cover-letter output.

- **Tier 1 — normalize (always safe):** any line-start bullet glyph (`-`, `–`, `*`) → `•`.
- **Tier 2 — validate:** flag `;` and `—` anywhere; hyphens legal only in `\w-\w` (inside compound words), anything else is a violation. Detect surviving `[PLACEHOLDER]` markers (reported to the user, not treated as violations).
- **Tier 3 — repair:** one scoped re-prompt to rewrite only offending lines. **[YOUR CALL]** if violations survive the retry: (a) deterministic last-resort substitution (`—`→`, `, `;`→`. `) with a logged warning — always terminates, occasionally awkward; or (b) hard-fail with a violation report — never ships awkward text, can strand the user. Recommend (a) for a personal tool.

Placeholders surviving into the final doc are surfaced in console output ("3 placeholders need your input before sending").

---

## 8. CLI surface

Same thin-subcommand pattern (ADR-020): `main.py` → `cli/` → service → repository port. No UI (a single-user fire-and-forget tool's interaction surface is "occasionally run a command referencing a job id"; a UI would reintroduce the long-running process the design avoids).

```
python -m src.main                                   # existing run (now writes through repo)
python -m src.main tailor       --job-id <id> [--provider ...]
python -m src.main cover-letter --job-id <id> [--provider ...]
python -m src.main mark         --job-id <id> --status <status> [--note "..."]
python -m src.main jobs         [--status <status>]   # list; default shows actionable states
```

The delivery email embeds the ready-to-paste `tailor` / `mark` command per listing, recovering most of the "click from the email" convenience at zero architectural cost (the email is still one-way; it just hands you the invocation).

---

## 9. Config surface (`.env`, documented in `docs/env.md`)

```env
# Persistence
DB_PATH=data/agent.db

# Re-evaluation
REEVALUATE_AFTER_DAYS=30          # skip re-scoring a known job newer than this

# Tailoring (provider allowlist: openai | anthropic ONLY — resume privacy)
TAILOR_PROVIDER=anthropic         # default: falls back to EVALUATOR_PROVIDER if in allowlist
TAILOR_MODEL=                     # optional per-provider model override
TAILOR_OUTPUT_DIR=output/tailored

# Cover letters (same allowlist)
COVERLETTER_PROVIDER=anthropic
COVERLETTER_MODEL=
COVERLETTER_OUTPUT_DIR=output/cover_letters
VOICE_SAMPLES_DIR=docs/voice      # user-editable writing samples (see §6)
```

Cost rates reuse the existing `*_COST_PER_1M` vars. No new pricing vars — generation cost uses the same per-provider rates as evaluation.

---

## 10. Build sequence

Each step de-risks the next. 1→2→3 is ordered; 4 and 5 are swappable.

1. **Persistence foundation** — `JobRepositoryPort`, SQLite adapter, schema, migrations. Rewire the existing pipeline to write through it. No user-visible feature yet, but runs now leave durable state.
2. **Dedup (feature 1)** — entity split, fingerprint matching, near-miss logging, skip-already-evaluated. Starts saving LLM cost immediately; exercises the store with real data before anything user-facing depends on it.
3. **Status tracker (feature 2)** — `mark` + `jobs` commands, status history, transition validation, suppression filter.
4. **Resume tailoring** — `ResumeTailorPort` + adapters + writer + formatting validator, reading from the repository.
5. **Cover letters** — sibling port + writer, plus the voice-profile design pass.

---

## 11. ADR set (for `docs/adr.md`)

Draft records to append (next numbers, standard format). Summarized here; I can write them out verbatim in your ADR style on request.

- **ADR-022 — SQLite persistence via `JobRepositoryPort`.** Supersedes the Phase-2 deferral in ADR-007. Context: three features (dedup, tracking, generation-lookup) need cross-run identity and mutable state a flat file can't serve. Decision: SQLite, single file, behind a repository port, no ORM. Consequences: first durable state; Postgres remains a future one-adapter swap; ADR-007's CSV stays as display output.
- **ADR-023 — `CanonicalJob` / `JobSighting` split with exact-fingerprint dedup.** Context: cross-provider duplicates break URL-hash identity. Decision: canonical position vs. platform sighting; exact fingerprint only, near-misses logged. Consequences: dedup saves re-evaluation cost; fuzzy matching deferred behind logged evidence.
- **ADR-024 — Job lifecycle tracker with status history.** Context: user wants application tracking, not just dismissal. Decision: status state machine + append-only `status_history`; suppression rule excludes acted-on jobs from future runs. Consequences: richer than a flag; transition validation lives in the core.
- **ADR-025 — Time-based re-evaluation, appended.** Decision: re-evaluate only when the latest evaluation is older than `REEVALUATE_AFTER_DAYS`; append, never overwrite; store JD hash to enable a future content-triggered mode. Consequences: score history preserved; content-trigger switch-on needs no migration.
- **ADR-026 — Sibling generation ports (`ResumeTailorPort`, `CoverLetterPort`) + docx writer ports.** Decision: narrow sibling ports sharing adapter internals; provider allowlist enforced at startup; structured output entities; deterministic formatting validator in core; `.docx`-only, path-logged. Consequences: cover letters extend the pattern without modification; resume-storage feature strengthens validation via the same interface.

---

## 12. Decisions still yours

- **Repair strategy** when formatting validation fails after one retry (§7) — auto-substitute vs. hard-fail.
- **Voice/tone mechanism** for cover letters (§6) — least-specified piece; recommend a dedicated brainstorm before step 5.
- **Generic vs. sibling generation ports** (§6) — recommend siblings; confirm before writing the first generation adapter.
- **Normalization aggressiveness** for the fingerprint (§3) — how much title/location noise to strip; affects dedup hit rate.
- **Whether `jobs` needs richer output** — e.g. filtering, sorting, showing latest score — or stays a simple status list.

Dependency to track: the resume-storage-improvement feature must enrich `Resume` **in place** for §6's zero-change assumption to hold.
