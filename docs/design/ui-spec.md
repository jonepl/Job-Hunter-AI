# UI Specification — Job Hunter AI Web

The screen, component, and state contract for the React SPA. Pairs with
`vertical-story-split.md` (stories, decisions, backend design) and
`adr-additions.md` (why). Derived from the as-built Claude Design screens plus the
seven reconciliation changes in that spec's §14.

**Read this before writing any component.** It is the source of truth for what
exists on screen; the design file is the source of truth for how it looks.

---

## 1. Stack (ADR-023)

React 18 + TypeScript + Vite · TailwindCSS · React Query v5 · Jest + React Testing
Library (unit/integration) · Playwright (E2E).

- Tailwind `theme.extend` is generated from `tokens.css` — never hardcode a hex.
- `.claude/rules/design.md` governs component conventions.
- All server state goes through React Query. No `useEffect` fetching.
- A typed API client in `web/src/api/` is the **only** place `fetch` is called.

## 2. Design system anchors

| Token | Value | Use |
|---|---|---|
| Accent (verdigris) | `#0F6B66` | Primary actions, active nav, threshold rail fill |
| Qualifying | `#1F8A4C` | Scores ≥ threshold |
| Near-miss | `#B7791F` | Scores below threshold |
| Background | `#F7F8FA` | App canvas |
| Display | Bricolage Grotesque | Headings, job titles |
| Body | Inter | Everything else |
| Data | IBM Plex Mono | Scores, cron expressions, keys, counts |

**Threshold rail** is the signature component: a 0–100 track with the score as fill
and a tick at the qualifying threshold. It appears on every job card and in the
detail pane. Build it once, reuse everywhere.

---

## 3. Information architecture

The IA is **run-centric** — `profile → run → matches`. This is deliberate and
correct for a scheduled agent. `TRACKED` adds a second, durable axis without
replacing it.

```
┌───────────────────────────────────────────────────────────────────────┐
│ Job Hunter AI   [active profile ▾] [Run search now]  Threshold 75  AR │
├──────────────┬─────────────────────────┬──────────────────────────────┤
│ LEFT RAIL    │ MIDDLE COLUMN           │ RIGHT DETAIL PANE            │
│              │ (driven by left rail)   │ (driven by middle selection) │
│ TRACKED   5  │                         │                              │
│  ● Applied 3 │  Run header             │  Title / company / location  │
│  ● Started 1 │  ├ match count          │  Provider badge SET          │
│  ● Interv. 1 │  ├ pre-filtered count → │  Threshold rail + score      │
│              │  └ label filters        │  Generation chips            │
│ SEARCH       │                         │  Status dropdown · Save ★    │
│ PROFILES  +  │  JobCard[]              │  Meta grid                   │
│  Product Des.│   title / co / badges   │  Why this matched            │
│  UX Des · SF │   threshold rail        │  About the role              │
│  …           │   salary · age · status │  Open job posting ↗          │
│              │                         │                              │
│ RUN HISTORY  │                         │                              │
│  Today 8:00  │                         │                              │
│  …           │                         │                              │
└──────────────┴─────────────────────────┴──────────────────────────────┘
```

**Left rail is the "what am I looking at" selector.** Three sources drive the
middle column:

| Source | Middle column shows |
|---|---|
| `TRACKED` | Cross-run list of `{applied, started, interviewing}` — same `JobCard` |
| A search profile | That profile's latest run |
| A run-history entry | That specific run's matches |

`TRACKED` sits **above** `SEARCH PROFILES`. Same `JobCard`, no new page, no new nav
bar. Selecting `TRACKED` is not scoped to a profile.

---

## 4. Domain vocabulary (must match backend)

### `JobStatus` — nine states

| Status | Set by | Selectable in UI | Group |
|---|---|---|---|
| `new` | machine | ✗ (display only) | machine |
| `evaluated` | machine | ✗ (display only) | machine |
| `pre_filtered` | machine | ✗ (display only) | machine |
| `applied` | human | ✓ | active pipeline |
| `started` | human | ✓ | active pipeline |
| `interviewing` | human | ✓ | active pipeline |
| `offer` | human | ✓ | terminal (celebratory) |
| `rejected` | human | ✓ | terminal |
| `not_interested` | human | ✓ | terminal |

Transitions are **permissive (any → any)**. Two UI obligations:
- Reactivating a terminal status (`rejected` / `not_interested` → any active) opens
  a soft confirm: *"This was marked rejected — reactivate?"* Confirm lives in the
  client; the API permits the write regardless.
- Setting a status to its current value is a **no-op** (no request, no history row).

### `saved` is NOT a status
A boolean bookmark, orthogonal to `JobStatus`. A job can be `saved` **and**
`applied`. Rendered as a star toggle beside the status dropdown. Never a dropdown
option.

### Score
Overall `0–100` plus a **nine-category breakdown**: role alignment, technical stack
match, system design/architecture, impact & metrics, domain/industry experience,
problem-space relevance, ownership & leadership, resume signal quality, career
trajectory. Plus `hire_recommendation` and `seniority_level`.

---

## 5. Components

### 5.1 `<ThresholdRail score threshold nearMissFloor />`
0–100 track, fill to `score`, tick at `threshold`. **Three fill states, not two:**
`qualify` (green) when `score >= threshold`; `nearmiss` (amber) inside the near-miss
band below threshold; `below` (gray) beneath that band. Color is never decorative.
Used on `JobCard`, the detail pane, and score-colored table cells.

> ✓ **Resolved (ADR-033):** the near-miss band is a fixed-width offset below the
> active threshold — `NEAR_MISS_BAND` (default `15`). `nearMissFloor = threshold −
> NEAR_MISS_BAND`. The backend returns `threshold` and `nearMissFloor` **per job**
> (threshold is per-profile, stored on the evaluation row); `<ThresholdRail>` reads
> the job's own values, never a global. One rule feeds the rail, the email cards, the
> CSV, and the zero-results suggestion. See `.claude/rules/design.md` and ADR-033.

### 5.1b `<ScoreChip score threshold />`
Mono, 600 weight, pill radius, 6px `currentColor` dot. Same three states:
`92 · Qualifying` / `71 · Near-miss` / `48 · Below`.

### 5.2 `<StatusPill status />`
Nine variants. Visual grouping: machine (muted/neutral), active pipeline (accent),
terminal (subdued), `offer` (celebratory emphasis).

### 5.3 `<ProviderBadges platforms />`
**A set, not one badge.** Dedup collapses the same posting across platforms.
Card: `via LinkedIn, Indeed`. Detail: two badges. Never assume length 1.

### 5.4 `<GenerationChip kind state />` — the five-state component
`kind` ∈ `{resume, cover_letter}`. One component, five visual states:

| State | Render | Interaction |
|---|---|---|
| `empty` | `○ Cover letter` | Click → generate |
| `generating` | spinner + label | Disabled; polling |
| `failed` | `⚠ Retry` | Click → re-trigger |
| `ready` | `✓ Resume · Jul 5 ↓` | Click → download |
| `needs_review` | `⚠ Resume · Jul 5 ↓ · 2 to check` | Click → expand disclosure |

**`needs_review` disclosure — HARD PRIVACY CONSTRAINT.** Generated document content
is **never** rendered in the DOM. Output is download-only. The disclosure lists
**locations only**:

```
2 to check
  • Experience → date range
  • Summary → line 2
```

Never the offending text. This is the one component with a genuine design tension;
if the design file's solution differs from the above, **the design file wins** —
but the no-content rule is inviolable.

A third state note: `repaired` collapses into `ready` visually but carries a small
note — *"auto-fixed 1 formatting issue"* — surfaced on hover or beneath the chip.

### 5.5 `<StatusDropdown value onChange />`
Six selectable options (`applied`, `started`, `interviewing`, `offer`, `rejected`,
`not_interested`). Displays machine statuses as the current value when applicable,
but never offers them. Triggers the reactivation confirm per §4.

### 5.6 `<JobCard />`
Title · company · location · `<ProviderBadges>` · `<ThresholdRail>` · score ·
salary · posted-age · `<StatusPill>` when status is not `new`/`evaluated`.
Identical in the run view and the `TRACKED` view.

### 5.7 `<PreFilterCount n onReveal />`
Run header: `Showing 8 of 8 matches · 12 pre-filtered`. The count is a link;
clicking reveals an inline list of skipped jobs with the reason for each
(*"seniority mismatch"*). Inline disclosure, **not** a new screen.

---

## 6. Screens

### 6.1 Search (the hub)
Left rail (`TRACKED`, `SEARCH PROFILES`, `RUN HISTORY`) · run header
(match count, `<PreFilterCount>`, label filters, "Qualifying only" toggle) ·
`JobCard[]` · right detail pane.

**Detail pane contents:** title, company, location, work type; `<ProviderBadges>`;
score chip + `<ThresholdRail>` with threshold tick; **Generate documents** button
(with a split dropdown for resume vs cover letter); `<GenerationChip>` × 2;
`<StatusDropdown>` + `Save ★` toggle; "View original posting ↗"; meta grid
(salary / job type / posted / score); *Why this matched* (matched + missing
skills); *About the role*; *What you'll do*; provenance footer
(*Found by your Product Designer profile · via LinkedIn*).

### 6.2 Zero-results state
**A first-class screen, not an error.** The agent always delivers a report. Shows:
an explanation of what happened; the top near-miss jobs rendered as normal
`JobCard`s; the total evaluated this run; a **suggested lower threshold** with a
one-click apply.

### 6.3 Settings (five sub-screens)
Left config nav: Voice & tone · Run schedule · Search profiles ·
Evaluator provider · Master resume.

| Screen | Contents | Notes |
|---|---|---|
| **Voice & tone** | Tone preset (`direct`/`warm`/`formal`/`bold`), first-person toggle (`first person`/`implied`), free-text **style notes**, live preview | **No writing samples** (ADR-030). Style notes are the high-fidelity mechanism. Preview is the tuning loop. |
| **Run schedule** | Presets (Hourly/Daily/Twice daily/Weekdays), editable cron expression, timezone, **Next 3 runs** preview | Live edit reschedules in-process — no restart (ADR-032) |
| **Search profiles** | List with query, scrapers, next-run time, Edit/Pause/Resume, `+ New profile`; the editor sets the per-profile **match threshold** (slider 0–100 + mono value, qualify-zone rail, near-miss band) | Threshold is per-profile (ADR-033); folded into the profile editor — no longer a standalone section |
| **Evaluator provider** | Provider cards with cost/job, **masked API key + Replace**, **`ENRICHMENT_MODE` shadow/enforce toggle** | Key is **write-only**: masked suffix on read, replacement on write (ADR-031) |
| **Master resume** | File provenance (name, version, upload date, size, parsed skills/roles), Download/Replace, drop zone, **version history + Restore** | **Never preview resume content** (ADR-028) |

### 6.4 Universal states
Every list view implements: **loading**, **empty**, **error**, plus the
zero-results state where applicable. Design these; do not leave them to chance.

---

## 7. API surface the UI consumes

Endpoints under `/api`. The SPA is served from `/` by the same FastAPI process
(same origin, no production CORS).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/jobs?status=&profile_id=&run_id=&saved=` | List (drives all three middle-column sources) |
| `GET` | `/api/jobs/{id}` | Detail fan-out: sightings, history, evaluation, generations |
| `PATCH` | `/api/jobs/{id}/status` | `{status, note?}` → writes `status_history` |
| `PATCH` | `/api/jobs/{id}/saved` | `{saved: bool}` |
| `POST` | `/api/jobs/{id}/generate` | `{kind: resume\|cover_letter}` → `{generation_id}` |
| `GET` | `/api/generations/{id}` | Poll → `{status, outcome, locations[], path}` |
| `GET` | `/api/generations/{id}/download` | Streams the `.docx` |
| `GET` | `/api/runs?profile_id=` | Run history |
| `GET` | `/api/runs/{id}` | Run detail incl. `pre_filtered[]` with reasons |
| `POST` | `/api/runs` | Trigger "Run search now" |
| `GET/PUT` | `/api/settings` | Operational settings; **secrets masked on read** |
| `PUT` | `/api/settings/secrets/{name}` | Write-only secret replacement |
| `GET` | `/api/resume` | Provenance + version history |
| `POST` | `/api/resume` | Multipart upload → parse → new version |

**Generation is async** (ADR-029): `POST /generate` returns immediately with a
`generation_id`; the client polls `GET /generations/{id}` via React Query
`refetchInterval` until a terminal `status`. A stuck `pending` times out to
`failed`; the chip offers Retry.

**No endpoint ever returns generated document content or full resume text.**
Only paths, provenance, outcome, and location hints.

---

## 8. React Query conventions

- **Query keys:** `['jobs', filters]`, `['job', id]`, `['runs', profileId]`,
  `['generation', id]`, `['settings']`, `['resume']`.
- **Status mutation** (`useMarkStatus`) is **optimistic**: update the cache, roll
  back on error, invalidate `['jobs']` and `['job', id]` on settle. Marking a job
  `not_interested` removes it from the triage list immediately.
- **Generation polling** (`useGeneration`): `refetchInterval` while
  `status === 'pending'`, `false` once terminal.
- **`saved` toggle** is optimistic too — it is a fast, low-stakes write.

---

## 9. Testing

| Tier | Tool | Covers |
|---|---|---|
| Unit / integration | Jest + RTL | Every component in every state (loading/empty/error/populated); `<GenerationChip>` in all five states; hooks against a mocked API client + RQ test wrapper |
| E2E | Playwright | Critical flows only, against a seeded SQLite fixture: triage → detail → mark applied → appears in TRACKED → generate → download |

Mirror the backend rule: **no real external calls.** Playwright runs against a
seeded local DB; generation is stubbed — no real LLM spend in CI.

A required test: **assert no endpoint response and no rendered DOM ever contains
generated document body text or raw resume text.** This is the privacy boundary,
enforced in tests, not just convention.
