# Feature: Search page redesign v2 — per-profile runs & the interactive rail

**Status:** Implemented (2026-07-26). Backend runs.profile_id (migration 11) +
`GET /runs?profile=`, `ProfileOut.next_run_at`; frontend per-profile rail history,
multi-select sequential batch runs, ⚙ ConfigureProfileModal, and the top-bar run
strip. See ADR-041.
**Date:** 2026-07-25
**Source design:** `docs/design/claude-design/job-hunter-ai-web-v2/Search.dc.html`
(markup lines 22–472; state/logic lines 475–957).
**Builds on (completed):** `docs/features/completed/search-screen-redesign.md` — the
three-column shell, filter model, card/detail anatomy, run-state panels, and generation
controls already shipped. **This plan is the v2 delta, not a re-spec of the whole screen.**
**Depends on:** `per-profile-scheduling.md`, which **ships first** and owns the schedule
half — per-profile `schedule_*` fields, `SchedulerManager.sync`, the
`run_scheduled_profile` single-profile run path, per-profile `next_run_at`, and the
`POST /runs?profile=id` trigger. This plan **consumes** all of that; it does not rebuild
it. The schedule-derived top-bar/modal surfaces here keep a graceful-degradation fallback
(see the conflicts table) purely as a safety net — by ship time the data will exist.

## What v2 adds over the shipped Search screen

The completed redesign deliberately **deferred** two things (its conflicts #1 and #2):
per-profile run history, and a run that targets a single profile. The v2 design turns
both on and layers interaction onto the rail. Concretely, the delta is:

1. **Per-profile run history.** The rail's Run-history section is scoped to the
   **selected profile** (not global), each row tagged **Scheduled** or **Ad-hoc**.
2. **Multi-select + batch run.** Checkboxes on profile rows, a **Select all** toggle,
   and a sticky **"Run N selected now"** button.
3. **Per-profile run trigger.** A ⚙ gear per row opening a **Configure profile** modal,
   and a per-profile **Run now** path.
4. **Per-profile status lines** in the rail — "Delivered · 8 matches", "Running now…",
   "Zero results · today 9:00 AM" — replacing today's static "location · threshold" line.
5. **Top-bar run strip.** "Running N profiles…" while a run is live, otherwise
   "Next scheduled run <when>".
6. **New-profile modal** gains a static schedule/threshold info line.

Everything else the mock shows (the "Viewing" box, threshold indicator, filter chips,
zero-results / run-failed / running panels, the generation split-button + five-state
chips, needs-review disclosure, status dropdown, save star, pre-filter reveal) is
**already built** — untouched here except where a conflict below says otherwise.

## Decisions locked in

- **A run targets one profile OR all profiles.** `POST /runs` with no arg stays the
  global "run all enabled profiles" batch (`profile_id` NULL — today's behavior). The
  per-profile and multi-select paths issue `POST /runs?profile=id` (the trigger defined
  in `per-profile-scheduling.md`), which tags the run with that profile. No run ever
  spans an arbitrary *subset*; multi-select is sugar (see next).
- **Multi-select "Run N selected" = sequential per-profile runs, client-orchestrated.**
  The existing single-flight guard (`RunService._active_run`) already forbids concurrent
  runs. The rail fires one `POST /runs?profile=id` at a time, polling each to a terminal
  status before the next. This **reuses** the guarantee "profiles run sequentially, not
  concurrently" for free — no new server-side queue, no new concurrency surface.
- **Schedule *editing* is out of scope — owned by `per-profile-scheduling.md`.** The v2
  Configure-profile modal intentionally carries only *what a profile searches for*
  (name, query, location, platforms) — matching the mock exactly (lines 408–436). The
  cron/frequency builder lives in that sibling plan's editor. This plan only **reads**
  schedule state (next-run time, scheduled-run tagging).
- **Run history is scoped by `runs.profile_id`, surfaced via `GET /runs?profile=id`.**
  This is the honest replacement for the completed redesign's global-history compromise.
- **Per-profile status line reuses existing profile metadata where possible.**
  `search_profiles.last_run_status` / `last_run_at` (migration 8) already back the
  status dot and timestamp; only the match **count** ("· 8 matches") needs the latest
  per-profile run's `qualifying`, read from `GET /runs?profile=id&limit=1`.

## Conflicts resolved

| # | Mock assumes | Reality today | Resolution |
|---|---|---|---|
| 1 | Run history scoped per profile (line 752, `runsFor(profile)`) | `runs` is global; no `profile_id` (`migrations.py:192`) | **Part A** adds `runs.profile_id`; rail reads `GET /runs?profile=id`. Legacy/global runs (`profile_id` NULL) are excluded from a profile's list. |
| 2 | Runs tagged **Ad-hoc** vs **Scheduled** (line 756) | `runs.trigger` exists (`web`/`scheduled`/`cli`) but the UI never reads it | Map `trigger`: `scheduled` → "Scheduled", `web`/`cli` → "Ad-hoc". No schema change. |
| 3 | "Run N selected" fires N profiles at once (line 604 `runProfiles(keys)`) | Single-flight guard: one run at a time | Client fires them **sequentially**, awaiting each terminal status. Button shows progress ("Running 2 of 3…"). |
| 4 | Top-bar "Next scheduled run tomorrow 8:00 AM" (line 41) | No per-profile schedule yet | Depends on `per-profile-scheduling.md`. When a `next_run_at` is available, show the soonest across enabled+scheduled profiles; **degrade** to hiding that half of the strip until then. |
| 5 | Config modal edits a profile inline from the rail (lines 408–436) | Profile editing lives only in Settings → Profiles (`ProfileSettings.tsx`) | Add a **`ConfigureProfileModal`** reusing the existing `PUT /api/profiles/{id}`; fields limited to name/query/location/platforms (the mock's set). |
| 6 | Pre-filter reveal lists *this run's* skipped jobs with reasons (lines 152–168, `prefilteredData`) | Enrichment skips aren't persisted per run/job; only aggregate `EnrichmentSummary` exists in-run | **Deferred.** The "N pre-filtered" link + reveal are dropped from this pass (carry-forward below). The already-shipped screen doesn't depend on them. |
| 7 | Per-row status "Delivered · 8 matches" (line 552) | `last_run_status`/`last_run_at` exist; per-profile count doesn't | Reuse profile metadata for dot + timestamp; read the count from the profile's latest run. |

## Scope of change

### Part A — Backend: attribute runs to a profile

- **Domain:** add `profile_id: int | None = None` to `RunRecord`
  (`src/core/domain/run_record.py`). NULL = a global "run all" batch.
- **Migration (next unused number — 11 if `per-profile-scheduling.md`'s migration 10 has
  landed, else 10):** `ALTER TABLE runs ADD COLUMN profile_id INTEGER;` No backfill —
  existing rows are honestly global (NULL). Mirror the append-only style of migration 9.
- **Repository (`sqlite_run_repository.py`):** round-trip `profile_id` in the column
  list (line 54) and the insert/update (line 78); add `list_recent(limit, profile_id=None)`
  filtering by `profile_id` when given.
- **`RunService`:**
  - `start_run(profile_id: int | None = None)` — when set, validate the profile exists
    and is enabled, store it on the record, and (in `execute_run`) run **only** that
    profile instead of `run_all_profiles`. The single-profile run path already exists —
    it's the one `per-profile-scheduling.md` factored out for `run_scheduled_profile`;
    call it, don't duplicate it.
  - `recent_runs(limit, profile_id=None)` passes the filter through.
- **API (`routers/runs.py`):**
  - `POST /runs` gains an optional `profile: int | None = Query(None)` → `start_run(profile)`.
    **This trigger is delivered by `per-profile-scheduling.md` (ships first); consume it
    here — do not re-add it.** Likewise the single-profile `execute_run` path is the one
    that plan factors out for `run_scheduled_profile`; reuse it.
  - `GET /runs` gains optional `profile: int | None = Query(None)` → `recent_runs(limit, profile)`.
  - Add `profileId` to `RunOut` (`schemas.py` + regenerate `web/src/api/types.ts`).

### Part B — Frontend data hooks

- `web/src/hooks/useRuns.ts`: `useRuns(profileId?: number)` — key `["runs", profileId ?? "all"]`,
  calls `api.listRuns(profileId)`. Keep the running-poll behavior. Add
  `useStartRun` overload accepting a `profileId` and a small **sequential batch runner**
  (`useRunProfilesSequentially`) that awaits each run to terminal before starting the next
  and exposes `{ current, total, running }` for the button label.
- `web/src/api/client.ts`: `listRuns(profileId?)`, `startRun(profileId?)`.

### Part C — Rail interactivity (`SearchRail.tsx`, `ProfilesSection`)

- **Checkbox** per profile row (18px, accent when checked) driving a `Set<number>`
  selection held in `JobList` (React state only — no storage).
- **Select all / Clear** toggle in the section header beside **+ New**.
- **⚙ gear** per row → opens `ConfigureProfileModal` for that profile (Part F).
- **Per-profile status line:** replace the current "location · threshold" line with the
  status dot + text derived from `last_run_status` + latest per-profile run count
  (`runningNow`/`Delivered · N matches`/`Zero results · <when>`/`Not scheduled`).
- **Sticky "Run N selected now"** button (bottom of the profiles section) — disabled with
  no selection; label reflects `useRunProfilesSequentially` progress; respects the
  single-flight guard (any error → surfaced, batch halts).
- **Run history** (`RunHistorySection`): take a `profileId`, call `useRuns(profileId)`,
  and render the **Ad-hoc/Scheduled** source badge (conflict #2). Header caption shows the
  viewed profile's name. Rows stay non-interactive (jobs still carry no `run_id` — the
  completed redesign's conflict #1 stands for *job* filtering).

### Part D — Top-bar run strip (`SearchTopBar.tsx`)

- Add a `SearchRunStrip` rendered in the `<TopBar>` center-left: shows
  "Running N profile(s)…" (spinner) while any run is active, else
  "Next scheduled run <when>" from the soonest per-profile `next_run_at`
  (conflict #4 — hidden until `per-profile-scheduling.md` supplies it). Keep the existing
  "Viewing" box + threshold indicator.

### Part E — New-profile modal (`NewProfileModal.tsx`)

- Add the static info line (mock line 461): "Runs on your schedule — <cadence> · threshold
  {profile.scoreThreshold}". Cadence text comes from the profile's schedule once
  `per-profile-scheduling.md` lands; until then show "Runs when you trigger it".

### Part F — Configure-profile modal (new `ConfigureProfileModal.tsx`)

- Mirror `NewProfileModal` but pre-filled and calling `PUT /api/profiles/{id}`. Fields:
  name, query, location, platforms (the mock's set only). On save, invalidate the profiles
  query so the rail row updates. **No schedule fields** (owned by the sibling plan).

### Tests

- **Python:** `RunRecord.profile_id` round-trip; migration adds the column; repository
  `list_recent(profile_id=…)` filters; `RunService.start_run(profile_id)` runs one
  profile, tags the record, and honors the single-flight guard; `GET /runs?profile=` and
  `POST /runs?profile=` endpoints.
- **Web:** `useRuns(profileId)` keys/fetches per profile; `useRunProfilesSequentially`
  runs one at a time and stops on error; `SearchRail` — checkbox selection, Select-all,
  per-profile status line, Ad-hoc/Scheduled badge, sticky run button states;
  `ConfigureProfileModal` submit → `PUT`; `SearchRunStrip` running vs next-run vs degraded.

### Docs / rules

- `.claude/rules/output-and-scheduling.md`: note runs are now attributable to a single
  profile (`runs.profile_id`); the sequential guarantee for multi-select comes from the
  client firing per-profile runs one at a time under the single-flight guard.
- `docs/architecture.md`: update the runs data model (add `profile_id`) and the Search-rail
  description (per-profile history + batch runs).
- `docs/adr.md`: new ADR — "Runs are attributable to one profile; per-profile run history
  and multi-select batch runs; multi-select serializes via the single-flight guard."
- `docs/env.md`: no new variables.

## Verification

- `pytest tests/unit/ -v` — green.
- Web unit tests — green.
- Manual smoke: select two profiles → "Run 2 selected now" fires them **sequentially**
  (second waits for the first to finish); each new run appears under **its** profile's Run
  history tagged **Ad-hoc**; a scheduled fire (once `per-profile-scheduling.md` is in)
  shows **Scheduled**; the ⚙ modal edits a profile and the rail row updates live.

## Sequencing

1. `per-profile-scheduling.md` ships first, delivering `POST /runs?profile=id`, the
   `run_scheduled_profile` single-profile path, per-profile `next_run_at`, and the
   `schedule_*` fields. This plan starts from that tree.
2. Part A (backend attribution — the `runs.profile_id` migration + `GET /runs?profile=`;
   the `POST` trigger is already present) → Part B (hooks) → Parts C–F (UI).
3. The top-bar "Next scheduled run" (Part D) and the New-profile cadence line (Part E)
   read schedule data that now exists; the degradation fallback stays only as a safety net
   for an unscheduled profile.

## Out of scope (carry-forward)

- **Pre-filter reveal (conflict #6).** Listing a run's pre-filtered/skipped jobs with
  reasons needs per-job enrichment-skip persistence (a new table or column) — not built.
  Track separately; the "N pre-filtered" link stays off until then.
- **Clicking a run to filter the job list.** Jobs still carry no `run_id`; run-history
  rows remain non-interactive. Unchanged from the completed redesign.
- **The scheduled-vs-manual double-run footgun — resolved upstream, verify here.**
  This feature adds the surface that makes the race easy to hit (per-profile "Run now" +
  multi-select), but the fix ships **before** it: `per-profile-scheduling.md` routes the
  scheduled run path through `RunService`'s single-flight guard, so a scheduled fire and a
  manual `POST /runs` cannot overlap. No new lock work here — but the manual-run smoke test
  below should confirm the guard holds against a scheduled fire, and if that fix somehow
  slipped upstream, it is a **blocker for this feature**, not a carry-forward.
