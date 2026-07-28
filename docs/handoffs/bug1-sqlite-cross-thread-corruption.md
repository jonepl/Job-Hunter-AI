# Handoff — Bug 1: SQLite `file is not a database` from unsynchronized cross-thread access

**Status:** RESOLVED (2026-07-27) — all six repositories on a file now share **one**
`LockedConnection` (`src/adapters/repository/connection.py`), and a single process-wide
per-file `threading.RLock` serializes every access (rows eager-fetched under the lock).
A single shared connection also avoids the cross-connection WAL-writer deadlock that a
per-file lock over *separate* connections introduces (measured: per-op locking over six
connections deadlocked for the full `busy_timeout` on a reachable path — a threadpool
`update_settings` write concurrent with the pipeline's jobs write). Repro tests in
`tests/unit/adapters/repository/test_connection.py`; ADR-034 §1 amended with the
correction. Bugs 2–5 below remain out of scope.
**Severity:** critical (data-layer corruption; takes down the whole web app for the rest of the process)
**Source defect log:** `docs/defects/search-profile-run-failure.log`
**Owning session goal:** make concurrent DB access safe so a web-triggered run can never corrupt the SQLite connection state.

---

## TL;DR for the next session

During a web-triggered run, the pipeline writes to SQLite on the **event-loop thread**
while the client polls `GET /runs/{id}` every 2 s on **uvicorn threadpool threads**. All
repositories open their connections with `check_same_thread=False` and rely **only** on
`PRAGMA busy_timeout` for safety. That is insufficient: `busy_timeout` arbitrates lock
contention *between transactions*, but does **not** make a `sqlite3.Connection` safe for
concurrent use by multiple OS threads, nor protect the shared WAL index (`-shm`) across
the several connections open on the same file. The race corrupts the in-memory/WAL-index
state and SQLite starts raising `sqlite3.DatabaseError: file is not a database` on **every**
connection to `data/agent.db` until the process restarts.

**Fix direction:** serialize all connection access behind a real Python lock (see
Options below). Do **not** "fix" this by raising `busy_timeout`.

---

## How we know it's connection-state corruption, not disk corruption

The database file on disk is **valid right now**, after the incident:

```
$ sqlite3 data/agent.db "PRAGMA integrity_check;"
ok
$ file data/agent.db
data/agent.db: SQLite 3.x database, ... schema 4, UTF-8, ...
```

Yet at the time of the run, every connection raised `file is not a database`. Also telling:
`data/agent.db` was last written **Jul 19**, while `data/agent.db-wal` (354 KB) and
`data/agent.db-shm` are from the run day. So the committed pages live in the WAL, the
main file is intact, and a restart rebuilds the `-shm` from the WAL — which is exactly why
it verifies `ok` now. That signature (all connections fail simultaneously + on-disk file
is clean + big uncheckpointed WAL) is the fingerprint of shared WAL-index / connection
corruption from concurrent thread access, **not** a damaged file.

---

## Evidence trail in the defect log

- Lines 20–118: ~50 consecutive `GET /api/runs/{id}` polls (React Query's 2 s
  `refetchInterval` while the run is `running`). These run on threadpool threads.
- Line 119: `Profile 2 failed: file is not a database` — the pipeline's **write** dies
  (a `save_job` / `record_sighting` / dedup read inside `JobSearchService.run`).
- Lines 121–489: every subsequent `GET /api/jobs` → `500`, all with the same
  `sqlite3.DatabaseError: file is not a database` at `sqlite_repository.py:66`
  (`list_jobs`). One connection's corruption is visible from all of them because they
  share the file's `-shm`.

---

## Where the concurrency actually collides

Two threads touch connections on the same DB file at overlapping times:

1. **Event-loop thread** — `RunService.execute_run` is `async` and is scheduled as a
   FastAPI `BackgroundTask` (`src/api/routers/runs.py:57`). The pipeline
   (`JobSearchService.run`, `src/core/services/job_search_service.py`) makes **blocking**
   `sqlite3` calls directly on the loop: dedup reads (`find_by_fingerprint`,
   `find_near_misses`, `get_seen_on`), then Step 3.5 writes (`save_job`,
   `record_sighting`). `RunService` also writes the `runs` row here (start + final update).
2. **Threadpool threads** — the sync route handlers `GET /runs/{id}` (`poll_run`),
   `GET /runs`, and `GET /jobs` are plain `def`, so FastAPI runs them via
   `run_in_threadpool`. During a run the client polls `GET /runs/{id}` every 2 s.

`check_same_thread=False` (set in every repo `__init__`) permits this cross-thread use; the
code assumes `busy_timeout` covers it. It does not.

### The false-comfort comments to correct

- `src/adapters/repository/sqlite_repository.py:49–51` — the `check_same_thread=False`
  comment claiming "all writes still funnel through this one instance, and busy_timeout
  serializes any real contention." Both halves are misleading (see below).
- `src/adapters/repository/factory.py:24–26` — "every profile … writes through a single
  JobRepositoryPort." True per-table, but there are **six** independent connections on the
  same file (jobs, resume, generation, settings, profile, run), so "one instance" is not a
  whole-file guarantee.

---

## Affected files (all six open a connection the same way)

Each has the identical `sqlite3.connect(db_path, check_same_thread=False)` +
`PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout` + `apply_migrations` block in `__init__`:

- `src/adapters/repository/sqlite_repository.py` (jobs)
- `src/adapters/repository/sqlite_run_repository.py` (runs)
- `src/adapters/repository/sqlite_resume_repository.py`
- `src/adapters/repository/sqlite_generation_repository.py`
- `src/adapters/repository/sqlite_settings_repository.py`
- `src/adapters/repository/sqlite_profile_repository.py`

Factory / wiring context:

- `src/adapters/repository/factory.py` — per-`DB_PATH` singleton caches for each repo type.
- `src/api/deps.py` — module-scope singletons for the run/settings/generation services so
  the background task and the poll share one instance (and its connection).
- `src/orchestration/service_factory.py` — `build_run_service` / `build_service` wiring.

Referenced ADR: **ADR-034 §1** ("route all writes through one instance,
`busy_timeout` + short per-op commits"). This handoff shows §1 is necessary but **not
sufficient** — update the ADR when the fix lands.

---

## Recommended fix

The cleanest, lowest-risk fix is to **serialize every connection operation behind one
process-wide lock**, because all six connections share one file and SQLite's WAL index is
the shared resource being corrupted.

### Option A (recommended) — one shared `threading.Lock` guarding every `execute`/`commit`

- Introduce a single module-level `threading.RLock` shared by **all** repositories on the
  same `DB_PATH` (the file, not per-repo). A small mixin or a thin connection wrapper that
  acquires the lock around every `execute` / `executescript` / `commit` keeps it in one
  place and avoids touching every method by hand.
- Because writes are short (per-op commits already exist), lock hold times stay tiny; the
  2 s poll cadence means contention is negligible.
- Keep `busy_timeout` as a belt-and-suspenders for any genuinely separate process.

### Option B — connection-per-thread (thread-local connections)

- Give each thread its own `sqlite3.Connection` (WAL readers are cheap and safe across
  separate connections). Removes the single-object cross-thread hazard, but you still want
  a writer lock to avoid `database is locked` churn, and it multiplies open handles.

### Option C — move DB writes off the event loop into the guarded pool

- Wrap the pipeline's blocking DB calls in `run_in_threadpool` / a dedicated single-worker
  executor so all DB access happens on one serialized worker. More invasive to
  `JobSearchService` (touches the hexagon core), so prefer A unless there's a reason.

**Preference:** Option A. It's the smallest change, stays inside the adapter layer (no core
changes), and directly targets the shared-connection hazard.

---

## Acceptance criteria

1. A web-triggered run that persists jobs while `GET /runs/{id}` and `GET /jobs` are polled
   concurrently completes with **no** `file is not a database` error.
2. A reproduction test drives concurrent reads on one repo connection from multiple threads
   while another thread writes, and asserts no `sqlite3.DatabaseError`. Put it under
   `tests/unit/adapters/repository/` (mirror path rule, `.claude/rules/testing.md`).
3. `pytest tests/unit/ -v` is green.
4. The misleading comments (`sqlite_repository.py:49–51`, `factory.py:24–26`) are corrected
   to describe the real guarantee, and `docs/adr.md` ADR-034 is updated (or a new ADR added)
   to record that a Python-level lock — not `busy_timeout` — is what serializes threads.

---

## Reproduction

The natural repro is a real run with the web UI polling, but a faster unit-level repro:
open one `SQLiteJobRepository`, then from ~4 threads hammer `list_jobs()` while another
thread loops `save_job(...)`, all on the shared instance. Without a lock this raises
`sqlite3.DatabaseError` / `file is not a database` (and occasionally other SQLITE_MISUSE
errors) fairly quickly; with the lock it stays clean.

Reset a corrupted dev DB (if one is ever left behind) by checkpointing/restarting the
server — the on-disk file itself is fine; only the process's connection state was bad.

---

## Explicitly out of scope for this handoff (separate bugs from the same log)

These were identified alongside Bug 1 but are **not** part of this fix — do not scope-creep:

- **Bug 2 (HIGH):** a run whose only profile crashes is recorded as `succeeded` with
  `profiles_run=0` (`run_all_profiles` swallows the per-profile exception in
  `src/orchestration/scheduler.py:157–160`; `RunService.execute_run` then summarizes an
  empty `reports` list to "succeeded"). The failure never reaches the run record / UI.
- **Bug 3 (HIGH):** `GET /api/jobs` lets `sqlite3.DatabaseError` propagate to a raw 500
  (`src/api/routers/jobs.py:32`); no graceful degradation for a repository read failure.
- **Bug 4 (MEDIUM):** LinkedIn redirects description fetches to `authwall` and burns the
  full 8 s `wait_for_selector` timeout per job (log lines 50, 78, 99).
- **Bug 5 (MEDIUM):** Gemini pre-filter quota exhausted (log line 112) — circuit breaker
  tripped correctly (fail-open), but enrichment did nothing useful this run.

Fixing Bug 1 removes the root cause; Bug 2 is worth fixing regardless because it masks
*any* run failure, not just this one.
