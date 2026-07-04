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

- `SCHEDULE_ENABLED=true` (`.env` only — never a CLI flag) activates APScheduler
  mode (`src/scheduler.py`, `BlockingScheduler` + `CronTrigger`). `false` runs
  all profiles once and exits (`src/runner.py`).
- `SCHEDULE_CRON` and `SCHEDULE_TIMEZONE` configure the schedule.
- Each `SearchProfile` (`src/core/domain/search_profile.py`) gets its own service
  instance via `service_factory.build_service()`.
- Profiles run **sequentially, not concurrently** — prevents API flooding.
- Profile failures are caught and logged — a failing profile never stops the
  remaining ones.
- When CLI args are provided they override all profiles (use for testing only).

## Multi-profile config

- `PROFILE_COUNT` sets the number of active profiles; each profile is configured
  via `PROFILE_N_*` variables (query, location, work type, date posted, scrapers,
  score threshold, top results).
- Falls back to legacy single-search mode (`SEARCH_QUERY` etc.) when
  `PROFILE_COUNT` is not set.
