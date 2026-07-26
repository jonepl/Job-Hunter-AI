# Rules — Output, Reporting & Scheduling

## Output & reporting

- Results are delivered by **Gmail SMTP** (`smtplib`, HTML email) and saved as
  **CSV** to `output/results_<timestamp>.csv`. CSV and logs persist via Docker
  volume mounts.
- A `RunReport` is **always delivered** — never skip email or CSV output, even
  on a zero-result run.
- `SCORE_THRESHOLD` filters qualifying results. `TOP_RESULTS` is **optional** —
  when `None`, apply no cap and return all qualifying results; never assume it
  is set.
- Near-miss results:
  - Populated only when `qualifying_results` is empty.
  - Always capped at 5, sorted by score descending.
  - Use the condensed email format (no score-breakdown table).
  - Zero-result CSV filename is prefixed `no_results_`.
- `RunReport.suggested_threshold` floors the lowest near-miss score to the
  nearest 5 to suggest a lower threshold.

## Scheduling

- **Scheduling is per-profile (ADR-040).** Each `SearchProfile`
  (`src/core/domain/search_profile.py`) carries its own `schedule_cron`,
  `schedule_timezone`, and `schedule_enabled`. The web `SchedulerManager`
  (`src/orchestration/scheduler.py`) keeps **one APScheduler job per scheduled
  profile** (`profile-run-{id}`); the lifespan builds it **unconditionally** (no global
  enable gate) and `sync()` reconciles the jobs on every profile CRUD.
- **`SCHEDULE_ENABLED` is gone from the web path.** It is read **only** by the CLI's
  transitional warning; `python -m src.main` always runs all profiles once and exits
  (`src/orchestration/runner.py`, ADR-039). `SCHEDULE_CRON` / `SCHEDULE_TIMEZONE` no
  longer configure anything web-side.
- A trigger is registered only when `enabled AND schedule_enabled` — `enabled` (pause)
  and `schedule_enabled` are **distinct**; a paused profile never fires, and a manual
  "Run now" can run an *unscheduled* (but enabled) profile.
- **Each scheduled fire routes through the shared `RunService` single-flight guard**
  (the same instance the manual/API runs use, lifespan-injected). A scheduled fire and a
  manual `POST /runs` can never overlap; a scheduled fire creates a `RunRecord` with
  `trigger='scheduled'` (visible in the `/runs` feed).
- Profiles run **sequentially, not concurrently** — guaranteed by **two** layers: a
  single-worker `ThreadPoolExecutor` on the scheduler, **and** the shared class-level
  single-flight lock in `RunService` (which alone also covers scheduled-vs-manual).
- Profile failures are caught and logged — a failing profile never stops the
  remaining ones. When CLI args are provided they override all profiles (testing only).

## Multi-profile config

- **Profiles and global settings load from the DB, not `.env` directly (W7,
  ADR-031).** `SettingsService` seeds the `search_profiles` + `settings` tables from
  `.env` on first run and is authoritative thereafter; `bootstrap.load_profiles()`
  reads the store, and the run entrypoint bridges the global settings into
  `os.environ` (ADR-035). Edit profiles/settings in the browser Settings screen.
- `PROFILE_COUNT` + `PROFILE_N_*` (or legacy `SEARCH_QUERY`) are the **seed** source
  for the profile store on first run (query, location, work type, date posted,
  scrapers, score threshold, top results); after seeding, `.env` changes to these no
  longer take effect.
