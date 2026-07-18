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

# (version, sql) in ascending order. Append new migrations; never edit or
# renumber an applied one.
MIGRATIONS: list[tuple[int, str]] = [
    (1, _MIGRATION_1),
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
