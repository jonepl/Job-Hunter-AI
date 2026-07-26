# Feature: Per-profile scheduling with an intuitive cron builder

**Status:** Implemented (2026-07-26) — migration 10, guarded per-profile
`SchedulerManager`, per-profile builder UI, and the docs/rules/ADR-040 updates all
landed. See ADR-040.
**Date:** 2026-07-25
**Depends on:** `cli-scalpel-immediate-run-only.md` landing first (it deletes the
CLI `BlockingScheduler`, leaving the API-owned `SchedulerManager` as the only
scheduler — the base this feature rewrites). Build on the trimmed tree.

> **Design note (2026-07-26):** The concurrency architecture below was hardened in a
> grilling session that traced the actual code (`RunService`'s guard, the
> `SchedulerManager`, the SQLite repos, the routers). The load-bearing resolutions are
> collected under **"Resolved design decisions"** and threaded through sections B–D. The
> short version: the spec's original one-line "route the scheduled path through
> `RunService`'s single-flight guard" hid a real cross-thread race and an instance-sharing
> trap; both are now closed explicitly.

## Decision

Move scheduling from a **single global cron** to **per-profile schedules**, give it
an **intuitive builder UI** for people who don't know cron format, and **remove the
global schedule and `SCHEDULE_ENABLED` from the web path entirely**.

Each `SearchProfile` carries its own `schedule_cron`, `schedule_timezone`, and
`schedule_enabled`. The web `SchedulerManager` keeps **one APScheduler job per
scheduled profile** (`profile-run-{id}`), each firing a single-profile run on its own
cron. Cron remains the stored source of truth (APScheduler consumes it); the builder
just generates and parses it.

### Why

- **Different profiles want different cadences** — a global cron can't express "Senior
  SWE every weekday 8am, Data Eng weekly on Monday."
- **Cron is a usability wall.** A frequency + time-of-day + day-of-week builder covers
  virtually every real schedule; a raw-cron escape hatch covers the rest.
- **`SCHEDULE_ENABLED` is dead post-scalpel.** After the scalpel removes the CLI
  scheduler, the flag's only remaining consumer is the web boot gate. Per-profile
  `schedule_enabled` replaces it, so the flag is removed from the web path with no
  bridge. The web server always owns a `BackgroundScheduler`; profiles opt in
  individually.

### Model shift

- **Today:** one global cron (`AppSettings.schedule_cron/timezone`) → a single
  scheduler job → `run_scheduled_cycle` reloads **all** profiles → runs them
  **sequentially** in one cycle. Scheduled runs go straight to `run_all_profiles` and
  **create no `RunRecord`** — they are invisible to the `/runs` feed and never touch the
  single-flight guard.
- **Target:** each profile owns its schedule; `SchedulerManager` reconciles one job per
  scheduled profile; each job fires a **single**-profile run **through the same guarded
  `RunService` lifecycle the manual runs use** — so every scheduled fire creates a
  `RunRecord` and participates in single-flight.

## Confirmed decisions

- **No seeding.** New per-profile schedule fields default to unscheduled
  (`schedule_enabled=false`, empty cron). Existing profiles come up unscheduled after
  upgrade — the deliberate consequence of no-seed. A deployment currently
  web-scheduling via `SCHEDULE_ENABLED=true` will have all profiles unscheduled until
  each is turned on in the UI. Call this out in the release/ADR notes.
- **Global schedule removed entirely** — drop `AppSettings.schedule_cron/timezone` from
  the run path and remove the global "Run schedule" Settings section. Per-profile is the
  only source of truth.
- **`SCHEDULE_ENABLED` gone from the web path** — no global enable; each profile's
  `schedule_enabled` is the only switch. (`SCHEDULE_ENABLED` remains referenced **only**
  by the CLI's transitional warning in `src/main.py` from the scalpel — untouched here.)
- **Keep `enabled` (pause) distinct from `schedule_enabled`.** A trigger is registered
  only when `enabled AND schedule_enabled`; paused profiles never fire.
- **Manual run:** keep the global "Run all enabled profiles" button **and** add a
  **per-profile "Run now"** (`POST /runs?profile=id`). Both must respect the same
  single-flight guard as the global run.
- **Close the scheduled-vs-manual double-run footgun here (required scope).** The
  scheduled run path routes through the **same** `RunService` single-flight guard the
  manual/API runs use, so a scheduled fire and a manual `POST /runs` can never overlap.
  This is gated to this feature — not deferred to `search-page-redesign-v2.md`, which
  adds per-profile "Run now" + multi-select and would otherwise ship the easy-to-hit race
  with the fix still absent. Closes the tracked double-run issue (see the scalpel's
  out-of-scope note for the issue link).

## Resolved design decisions

These six resolutions replace the spec's original hand-wave and are the contract sections
B–D implement. Each closes a concrete break the code review surfaced.

1. **Guard atomicity — a class-level `threading.Lock`.** `RunService`'s single-flight
   guard is a **check-then-act** read today (`_active_run()` → then `save()` a `running`
   row) with no lock or DB constraint. It is safe *only* because manual runs are all
   serialized on uvicorn's single event loop. This feature adds a **second thread** (the
   APScheduler worker) calling the same guard, opening a genuine cross-thread TOCTOU: both
   can read `active() is None` and both start. **Fix:** a **class-level**
   `threading.Lock` on `RunService` wraps the check + insert in `start_run`. Class-level
   (not instance-level) so the lock is shared no matter which instance holds it.

2. **One guarded lifecycle serves all three run kinds.** `start_run(profile_id=None)` and
   `execute_run(run_id, profile_id=None)` serve **manual-all** (`profile_id=None`),
   **manual-one** (`POST /runs?profile=id`), and **scheduled-one** through the *same*
   locked `start_run`. This is the only shape where the lock actually protects every path.

3. **The scheduler shares the API's `RunService` instance (lifespan injection).** The API
   caches its `RunService` in `api/deps.py`; the scheduler lives in `orchestration/` and
   must not import `api/deps` (layering). A scheduler-built `RunService` would carry a
   *different* lock and the guard would protect nothing across paths. **Fix:** the
   **lifespan** (`api/main.py` — the one place that sees both layers) builds/gets the
   single `RunService` and **injects it into `SchedulerManager`**. The scheduled job
   calls `run_service.start_run(profile_id)` + `execute_run`. (Belt-and-suspenders: the
   class-level lock in #1 means even an accidental second instance stays safe.)
   *Consequence:* spec §B's "factor the per-profile path out of `run_all_profiles`"
   **is dropped** — `execute_run` reuses the already-injected `run_all_profiles` with a
   **one-element profile list**, so per-profile `last_run` stamping and cost tracking come
   for free.

4. **`profile_id` is an `execute_run` argument, not a stored column.** `execute_run(run_id,
   profile_id=None)` reloads the profiles fresh (ADR-031) and filters to the one profile,
   or runs all. **No `runs`-table migration** — the record's existing `trigger` column
   distinguishes source. (On restart the background task is lost and the row self-heals to
   `failed`, so nothing needs a persisted `profile_id`.)

5. **A blocked scheduled fire skips cleanly — never errors the trigger.** The manager's
   `_fire(profile_id)` callback wraps `start_run` in `try/except (RunInProgressError,
   NoProfilesError)` → log once at INFO → return. `coalesce=True` prevents pile-up.
   **Nuance:** `start_run(profile_id)` re-validates the profile is **exists AND enabled**
   only — **not** `schedule_enabled` (a manual "Run now" must be able to run an
   *unscheduled* profile). The `schedule_enabled` freshness re-check belongs to `_fire`
   (guarding the tiny race where a profile is unscheduled between `sync()` and the fire).

6. **Scheduled runs become visible in the `/runs` feed.** Because they now go through
   `start_run`, each scheduled fire creates a `RunRecord` stamped **`trigger='scheduled'`**
   (vs `'web'` for manual). The feed shows both, unfiltered — a net observability win over
   today's invisible scheduled runs. No new filter/endpoint. (The migration-7 `trigger`
   column already exists.)

### Guard flow (all three paths, one lock)

```python
class RunService:
    _guard = threading.Lock()  # CLASS-level — shared across instances

    def start_run(self, profile_id: int | None = None) -> RunRecord:
        with self._guard:                       # atomic check-then-act
            if self._active_run() is not None:
                raise RunInProgressError(...)
            profiles = self._settings_service.list_profiles()
            if profile_id is not None:
                p = _find(profiles, profile_id)
                if p is None or not p.enabled:  # NOT schedule_enabled
                    raise NoProfilesError(...)
            elif not any(p.enabled for p in profiles):
                raise NoProfilesError(...)
            trigger = "scheduled" if _from_scheduler else "web"
            return self._run_repo.save(RunRecord(status="running", trigger=trigger, ...))

    async def execute_run(self, run_id: str, profile_id: int | None = None) -> None:
        ...
        profiles = self._settings_service.list_profiles()
        profiles = [_find(profiles, profile_id)] if profile_id is not None else profiles
        reports = await self._run_all_profiles(profiles, self._service_factory, self._settings_service)
        ...
```

```python
# orchestration/scheduler.py — the injected callback
def _fire(self, profile_id: int) -> None:
    if not self._profile_still_scheduled(profile_id):   # fresh schedule_enabled re-check
        return
    try:
        run = self._run_service.start_run(profile_id=profile_id)   # scheduled trigger
    except (RunInProgressError, NoProfilesError) as exc:
        logger.info("scheduled run skipped: %s", exc)              # log once, don't error the trigger
        return
    asyncio.run(self._run_service.execute_run(run.id, profile_id=profile_id))
```

## Key constraint — preserve the sequential-run guarantee

`.claude/rules/output-and-scheduling.md` promises **"profiles run sequentially, not
concurrently — prevents API flooding."** That is free today (one job loops over
profiles). With independent per-profile triggers, two profiles scheduled at the same
time would fire **concurrently** and flood the scrapers/LLM.

**Mitigation (two layers, both required):**

1. **Single-worker executor.** Configure the `BackgroundScheduler` with a
   **`ThreadPoolExecutor(max_workers=1)`**, plus `coalesce=True`, `max_instances=1` per
   job, and a **generous, env-configurable `misfire_grace_time`** (see the residual-risk
   note — the APScheduler default of 1 s would *silently drop* an overlapping fire).
   Overlapping fires then queue on the single worker and serialize by construction.
2. **The `RunService` single-flight guard (§Resolved #1–3).** Even if the executor were
   misconfigured, the shared class-level lock rejects a second concurrent run. This is the
   half that also covers **scheduled-vs-manual** (the manual run executes on uvicorn's
   loop, *not* on the scheduler's executor, so the executor alone can't serialize it).

Both halves of the double-run footgun close here.

## Scope of change

### A — Domain + migration

- Add to `src/core/domain/search_profile.py`: `schedule_cron: str = ""`,
  `schedule_timezone: str = "UTC"`, `schedule_enabled: bool = False`.
- **Migration 10** on `search_profiles` (append-only, mirrors migration 8 in
  `src/adapters/repository/migrations.py`): three columns with the unscheduled
  defaults. No backfill.
- Update `src/adapters/repository/sqlite_profile_repository.py` read/write mapping to
  round-trip the new columns.
- **No `runs`-table migration** (§Resolved #4 — `profile_id` is a call argument).

### B — RunService + scheduler rewrite

**`src/core/services/run_service.py`:**

- Add a **class-level `threading.Lock`**; wrap the `_active_run()` check + `save()` in it
  inside `start_run` (§Resolved #1).
- `start_run(profile_id: int | None = None)` — validate the specific profile is
  **exists AND enabled** when `profile_id` is set (not `schedule_enabled`); stamp
  `trigger='scheduled'` vs `'web'`.
- `execute_run(run_id, profile_id: int | None = None)` — filter the reloaded profile list
  to the one profile, else all. Reuses the already-injected `run_all_profiles` unchanged.

**`src/orchestration/scheduler.py`:**

- **Delete** `SchedulerManager.start/reschedule(cron, tz)`, the module-level
  `run_scheduled_cycle` (now dead — only the old `_run` and its tests call it), and the
  single-`_JOB_ID` model.
- `SchedulerManager(run_service)` — constructed with the injected `RunService`.
- **`sync(profiles)`** — idempotent reconcile: add/reschedule a `profile-run-{id}` job for
  every profile where `enabled AND schedule_enabled`; remove jobs for profiles that are
  unscheduled / paused / deleted.
- **`_fire(profile_id)`** — the per-job callback (§Resolved #5): fresh `schedule_enabled`
  re-check → `start_run(profile_id)` under `try/except (RunInProgressError,
  NoProfilesError)` (log once, return) → `asyncio.run(execute_run(run.id, profile_id))`.
- Configure the `BackgroundScheduler` per the sequential-run constraint:
  `executors={'default': ThreadPoolExecutor(1)}`,
  `job_defaults={'coalesce': True, 'max_instances': 1, 'misfire_grace_time': <env>}`.
- Keep `run_all_profiles` (reused via `execute_run`), `get/set_scheduler_manager`.

**`src/api/main.py` lifespan:**

- Replace `_maybe_start_scheduler` with an **unconditional** build — **no env gate**, no
  `_DEFAULT_CRON`/`_DEFAULT_TIMEZONE`: get the shared `RunService` (`get_run_service()`),
  construct `SchedulerManager(run_service)`, call `sync(list_profiles())`, register it via
  `set_scheduler_manager`. Shutdown path unchanged.

### C — API

- Add the three schedule fields to `ProfileOut` / `ProfileIn` (+ `to_profile`/`from_profile`).
- **Relocate the live reconcile.** Today `settings.py`'s `update_settings` calls
  `manager.reschedule(...)` (lines 53–59) — **delete that block**. Instead, after any
  profile **create / update / delete**, `profiles.py` calls
  `get_scheduler_manager()` → `manager.sync(service.list_profiles())` (no-op when the
  manager is `None`, e.g. dev/API-only/tests that don't enter the lifespan). Mirror the
  `get_scheduler_manager` import pattern `settings.py` already uses.
- **Remove** `schedule_cron`/`schedule_timezone` from the three `AppSettings*` schema
  classes, `src/core/domain/app_settings.py`, and `settings_service.py`
  (`_ENV_MAP`, `_DEFAULTS`, `_to_app_settings`, `_to_values`). Keep `next_run_times` and
  the stateless `/api/settings/schedule/preview` endpoint — **reused per-profile**
  (cron+tz in, next-runs out). Optionally expose a computed `next_run_at` per profile.
- Add the per-profile run trigger (`POST /runs?profile=id` in `runs.py`) →
  `start_run(profile_id)` + `execute_run(run.id, profile_id)`, reusing the guard.

### D — Frontend

- New `web/src/lib/cron.ts` codec: `cronToSchedule(cron): ScheduleModel | null` and
  `scheduleToCron(model): string` (non-representable expressions → `null` → raw mode).
  Cron stays the stored value.
- Move the intuitive controls into the **profile editor** (`NewProfileModal.tsx` and the
  edit form in `ProfileSettings.tsx`): Enable-schedule toggle, frequency select,
  `type="time"` picker, day-of-week checkboxes, a read-only "Generated cron" mono line,
  and an **Advanced (raw cron)** escape hatch that round-trips.
- Timezone → searchable dropdown from `Intl.supportedValuesOf("timeZone")`, defaulting
  to the browser-detected zone.
- **Remove** the global `web/src/components/settings/ScheduleSettings.tsx`, its
  `SettingsNav.tsx` entry, and its test; drop `schedule_cron`/`schedule_timezone` from
  `web/src/api/types.ts` and `web/src/lib/settings.ts` (a TS break to fix in the same
  change).
- Per-profile status line: "Scheduled — next: Mon 8:00 AM" / "Not scheduled", plus the
  per-profile "Run now" button.

### Tests

- **Python:**
  - `SearchProfile` schedule fields + migration 10 round-trip.
  - `SchedulerManager.sync` add/reschedule/remove cases (mock APScheduler).
  - `_fire` single-profile path; single-worker executor serializes overlapping fires.
  - Per-profile run endpoint (`POST /runs?profile=id`).
  - **The scheduled-vs-manual footgun regression test:** a scheduled fire overlapping an
    in-progress manual run is rejected by the shared class-level lock (and vice versa) —
    and `_fire` logs-and-skips rather than erroring the trigger.
  - **Rewrites:** `tests/unit/orchestration/test_scheduler.py` (`start`/`reschedule`/
    `run_scheduled_cycle` gone → `sync`/`_fire`/serialization); `tests/unit/api/
    test_main_lifespan.py` (env gate gone → scheduler always built, `RunService` injected,
    `SchedulerManager` mocked so no real thread/DB); `tests/unit/api/test_settings_router.py`
    (reschedule-on-update + schedule fields removed); `test_profiles_router.py`
    (assert `sync()` called on CRUD via a mocked manager; schedule fields round-trip);
    any `AppSettings`/settings-service tests asserting the removed schedule fields.
- **Web:** `web/tests/lib/cron.test.ts` (codec round-trips + null cases); profile-editor
  tests for the builder, toggle, preview, and Advanced round-trip. Remove the old
  `ScheduleSettings.test.tsx`.

### Docs / rules

- Rewrite `.claude/rules/output-and-scheduling.md`: per-profile scheduling; the
  sequential guarantee now comes from the single-worker executor **plus** the shared
  single-flight lock; global schedule and `SCHEDULE_ENABLED` removed from the web path.
- `docs/env.md`: remove the global `SCHEDULE_CRON` / `SCHEDULE_TIMEZONE` /
  `SCHEDULE_ENABLED` web entries (or mark removed); document the new
  `SCHEDULER_MISFIRE_GRACE_SECONDS` knob.
- `docs/architecture.md`: update the run-mode table and the scheduling section.
- `docs/adr.md`: new ADR — "Scheduling is per-profile; `SchedulerManager` reconciles one
  job per profile; global schedule + `SCHEDULE_ENABLED` removed; sequential runs via a
  single-worker executor **and** a shared class-level single-flight lock; the scheduled
  run path routes through `RunService` (lifespan-injected, shared instance), closing the
  scheduled-vs-manual double-run footgun; scheduled runs now surface in the `/runs` feed
  as `trigger='scheduled'`."

## Residual risks (accept or handle)

- **`misfire_grace_time` — silent drops.** APScheduler's default is **1 s**: if the
  scheduler loop is briefly delayed while the single worker is busy on a long run, an
  overlapping fire is *silently skipped*. Set a generous, env-configurable value
  (`SCHEDULER_MISFIRE_GRACE_SECONDS`, default ~3600) + `coalesce=True`. The guard makes
  double-*runs* impossible regardless; this knob only prevents silent *skips*.
- **Self-heal timeout (1800 s) vs. a genuinely long run.** A run exceeding the timeout is
  healed to `failed` by a concurrent poll/`_active_run`, letting a new fire start (it
  queues behind the still-running one on the single worker — no concurrent pipeline, but
  an extra record and a `failed → succeeded` flip on the original id). Pre-existing;
  consider aligning the run-timeout to the real max run duration.
- **`runs` table growth.** Frequent scheduled fires add rows with no pruning today
  (manual runs have the same property, at lower volume). Ops note; not a blocker.
- **No-seed upgrade.** Existing `SCHEDULE_ENABLED=true` deployments come up fully
  unscheduled until each profile is turned on. Orphaned `schedule_cron`/`schedule_timezone`
  settings k/v rows in upgraded DBs are harmless (no migration to delete them).

## Verification

- `pytest tests/unit/ -v` — green.
- Web unit tests — green.
- Manual smoke: create two profiles with overlapping schedules, confirm they fire
  sequentially (single-worker executor), that a scheduled fire overlapping a manual run is
  rejected (guard) and logged-and-skipped, that scheduled runs appear in the `/runs` feed
  as `scheduled`, and that toggling/deleting a profile updates the scheduler live.

## Resolved here (was carry-forward)

The **scheduled-vs-manual** double-run footgun (a scheduled profile fire overlapping a
manual `POST /runs`) **is fixed in this feature** — see §Resolved #1–3 and section B: the
scheduled path routes through `RunService`'s **class-level-lock** single-flight guard on
the **same injected instance** the manual runs use. This was previously deferred across
the scalpel and this plan; it is now required scope here rather than sliding into
`search-page-redesign-v2.md`, which adds the surface (per-profile "Run now" +
multi-select) that makes the race easy to hit. Update the tracked double-run issue to
closed when this ships.
