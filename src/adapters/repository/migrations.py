"""Lightweight forward-only migration runner for the SQLite store (ADR-023).

Each story extends the schema by exactly what it reads or writes — the whole
schema is never built up front. B1 lands migration 1: the ``jobs`` and
``sightings`` tables. A ``schema_migrations`` table records what has run so an
existing database is upgraded in place, never re-applied.
"""

import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

# Migration 1 (B1) — jobs + sightings.
#
# The partial UNIQUE index on ``fingerprint`` enforces one row per canonical key
# while allowing many NULL fingerprints — a job whose identity normalizes to
# empty has dedup disabled and must never collide with another (ADR-024).
_MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS jobs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint         TEXT,
    fingerprint_version INTEGER NOT NULL,
    canon_company       TEXT NOT NULL,
    canon_title         TEXT NOT NULL,
    canon_location      TEXT NOT NULL,
    company             TEXT NOT NULL,
    title               TEXT NOT NULL,
    location            TEXT NOT NULL,
    url                 TEXT,
    description         TEXT,
    overall_score       INTEGER,
    threshold           INTEGER,
    near_miss_floor     INTEGER,
    match_result_json   TEXT,
    first_seen_at       TEXT NOT NULL,
    last_seen_at        TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_fingerprint
    ON jobs (fingerprint) WHERE fingerprint IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_company_title
    ON jobs (canon_company, canon_title);

CREATE TABLE IF NOT EXISTS sightings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id    INTEGER NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    platform  TEXT NOT NULL,
    url       TEXT,
    seen_at   TEXT NOT NULL,
    UNIQUE (job_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_sightings_job ON sightings (job_id);
"""

# Migration 2 (C) — the nine-state job lifecycle (ADR-025).
#
# ``status`` and ``saved`` land on ``jobs``; every existing row is an evaluated
# job, so the column defaults are correct. ``status_history`` is the append-only
# audit trail, and the backfill writes one creation row per existing job (from
# NULL → its current status at its ``first_seen_at``) so the trail is complete.
_MIGRATION_2 = """
ALTER TABLE jobs ADD COLUMN status TEXT NOT NULL DEFAULT 'evaluated';
ALTER TABLE jobs ADD COLUMN saved INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS status_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    note        TEXT,
    changed_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_status_history_job ON status_history (job_id);

INSERT INTO status_history (job_id, from_status, to_status, note, changed_at)
    SELECT id, NULL, status, NULL, first_seen_at FROM jobs;
"""

# Migration 3 (E1) — the master resume, stored once with version history (ADR-028).
#
# The resume is parsed once and cached here so runs stop re-parsing the PDF every
# time. Each upload is a new ``version``; the partial UNIQUE index on ``is_active``
# guarantees exactly one active version (the one runs read). No backfill — the store
# starts empty and a first run auto-seeds v1 from the mounted resume path.
_MIGRATION_3 = """
CREATE TABLE IF NOT EXISTS resumes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    version       INTEGER NOT NULL,
    filename      TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL,
    raw_text      TEXT NOT NULL,
    skill_count   INTEGER NOT NULL DEFAULT 0,
    role_count    INTEGER NOT NULL DEFAULT 0,
    is_active     INTEGER NOT NULL DEFAULT 0,
    uploaded_at   TEXT NOT NULL,
    parsed_at     TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_resumes_active
    ON resumes (is_active) WHERE is_active = 1;

CREATE INDEX IF NOT EXISTS idx_resumes_hash ON resumes (content_hash);
"""

# Migration 4 (F) — generated documents, one row per artifact (ADR-029/034 §3).
#
# F owns this table (§15 gap 4/7). Each tailored resume or cover letter records
# **provenance only** — never the document text (CLAUDE.md #2): the job it was for,
# the provider/model, the formatter ``outcome``, the ``.docx`` path, an optional
# repair note, and (for needs_review) a JSON array of structural location hints. No
# backfill — the store starts empty. W6 adds the async lifecycle column in
# migration 5.
_MIGRATION_4 = """
CREATE TABLE IF NOT EXISTS generations (
    id               TEXT PRIMARY KEY,
    job_id           INTEGER NOT NULL,
    kind             TEXT NOT NULL,
    outcome          TEXT NOT NULL,
    file_path        TEXT NOT NULL,
    provider         TEXT NOT NULL,
    model            TEXT NOT NULL,
    repair_note      TEXT NOT NULL DEFAULT '',
    review_locations TEXT NOT NULL DEFAULT '[]',
    created_at       TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);

CREATE INDEX IF NOT EXISTS idx_generations_job ON generations (job_id);
"""

# Migration 5 (W6) — the async generation lifecycle column.
#
# The browser's "Tailor"/"Cover letter" flow generates asynchronously: a row is
# created ``pending`` before the (slow) LLM call, then updated to ``ready`` when the
# ``.docx`` exists or ``failed`` on error/timeout. The default ``ready`` is correct
# for the synchronous CLI path, which only ever inserts a finished record. Timeout
# detection reuses ``created_at`` (the pending row's insert time) — no extra column.
_MIGRATION_5 = """
ALTER TABLE generations ADD COLUMN status TEXT NOT NULL DEFAULT 'ready';
"""

# Migration 6 (W7) — web-editable, persistent configuration (ADR-031).
#
# ``.env`` becomes a bootstrap **seed**: on first access these tables are populated
# from the environment and are authoritative thereafter. ``settings`` is a flat
# key/value store for the global scalars **and** secret values (API keys); the API
# never returns a raw secret, only a masked suffix + an "overridden vs .env" flag.
# ``search_profiles`` is the CRUD store for the search definitions (one row per
# profile), replacing the ``PROFILE_N_`` env-loading path at run time. JSON list
# columns (``work_types``, ``active_scrapers``) round-trip via ``json.dumps``.
_MIGRATION_6 = """
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    query           TEXT NOT NULL,
    location        TEXT NOT NULL,
    work_types      TEXT,
    date_posted     TEXT,
    active_scrapers TEXT NOT NULL,
    score_threshold INTEGER NOT NULL,
    top_results     INTEGER,
    position        INTEGER NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_profiles_position
    ON search_profiles (position);
"""

# (version, sql) in ascending order. Append new migrations; never edit or
# renumber an applied one.
MIGRATIONS: list[tuple[int, str]] = [
    (1, _MIGRATION_1),
    (2, _MIGRATION_2),
    (3, _MIGRATION_3),
    (4, _MIGRATION_4),
    (5, _MIGRATION_5),
    (6, _MIGRATION_6),
]


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply every migration not yet recorded, in ascending version order.

    Each migration runs in its own transaction and is recorded on success, so a
    partially-applied schema is never left behind.

    Args:
        conn: An open SQLite connection.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    conn.commit()

    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    for version, sql in MIGRATIONS:
        if version in applied:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, datetime.now().isoformat()),
        )
        conn.commit()
        logger.info("Applied database migration %d", version)
