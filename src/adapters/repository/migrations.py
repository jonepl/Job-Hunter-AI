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

# (version, sql) in ascending order. Append new migrations; never edit or
# renumber an applied one.
MIGRATIONS: list[tuple[int, str]] = [
    (1, _MIGRATION_1),
    (2, _MIGRATION_2),
    (3, _MIGRATION_3),
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
