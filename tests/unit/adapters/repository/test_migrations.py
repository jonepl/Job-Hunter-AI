"""Unit tests for the forward-only migration runner (migrations 3 + 4 + 5).

Migration 3 (E1) adds the ``resumes`` table; migration 4 (F) adds the
``generations`` table; migration 5 (W6) adds the async ``status`` column to it.
These tests prove each applies cleanly on a fresh database and upgrades an existing
store in place without touching any ``jobs`` row.
"""

import sqlite3
from datetime import datetime

from src.adapters.repository.migrations import MIGRATIONS, apply_migrations
from src.adapters.repository.sqlite_repository import SQLiteJobRepository
from src.core.domain.fingerprint import compute_fingerprint
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory

_NOW = datetime(2026, 7, 18, 9, 0, 0)


def _table_names(conn: sqlite3.Connection) -> set[str]:
    """Return the set of user table names in the database."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def _match_result() -> MatchResult:
    """Return a minimal valid MatchResult for seeding a job row."""
    categories = {
        "role_alignment": ScoreCategory(max=20, earned=18, reasoning="ok"),
        "technical_stack_match": ScoreCategory(max=15, earned=13, reasoning="ok"),
        "system_design_architecture": ScoreCategory(max=15, earned=12, reasoning="ok"),
        "impact_and_metrics": ScoreCategory(max=15, earned=12, reasoning="ok"),
        "domain_industry_experience": ScoreCategory(max=10, earned=8, reasoning="ok"),
        "problem_space_relevance": ScoreCategory(max=10, earned=8, reasoning="ok"),
        "ownership_and_leadership": ScoreCategory(max=10, earned=8, reasoning="ok"),
        "resume_signal_quality": ScoreCategory(max=3, earned=2, reasoning="ok"),
        "career_trajectory": ScoreCategory(max=2, earned=1, reasoning="ok"),
    }
    return MatchResult(
        job=Job(
            title="Senior Software Engineer",
            company="Acme Corp",
            location="Remote",
            url="https://example.com/1",
            description="A job.",
            platform="linkedin",
            scraped_at=_NOW,
        ),
        score=82,
        matched_skills=["Python"],
        missing_skills=[],
        summary="Strong fit.",
        seniority_level="Senior",
        years_experience_detected=8,
        hire_recommendation="Yes",
        score_breakdown=ScoreBreakdown(**categories),
    )


def _generations_columns(conn: sqlite3.Connection) -> dict[str, str]:
    """Return the ``generations`` table's column name → default expression."""
    rows = conn.execute("PRAGMA table_info(generations)").fetchall()
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    return {row[1]: row[4] for row in rows}


def test_migrations_create_all_tables_on_fresh_db():
    """A fresh database gains every table (incl. resumes + generations) and records all."""
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)

    tables = _table_names(conn)
    assert "resumes" in tables
    assert "generations" in tables
    assert "settings" in tables  # migration 6 (W7)
    assert "search_profiles" in tables  # migration 6 (W7)
    versions = [row[0] for row in conn.execute("SELECT version FROM schema_migrations")]
    assert versions == [v for v, _ in MIGRATIONS] == [1, 2, 3, 4, 5, 6]

    # Migration 5 (W6): the async status column exists and defaults to 'ready'.
    columns = _generations_columns(conn)
    assert "status" in columns
    assert columns["status"] == "'ready'"
    conn.close()


def test_migration_3_upgrades_existing_job_store_without_touching_jobs(tmp_path):
    """Opening a v1/v2 job store applies migration 3 and preserves every job row."""
    db_path = str(tmp_path / "agent.db")

    # Build a database at migrations 1+2 only, with a real job row.
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    for version, sql in MIGRATIONS:
        if version == 3:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, _NOW.isoformat()),
        )
    conn.commit()
    conn.close()

    repo = SQLiteJobRepository(db_path=db_path)  # opening applies migration 3
    job = Job(
        title="Senior Software Engineer",
        company="Acme Corp",
        location="Remote",
        url="https://example.com/1",
        description="A job.",
        platform="linkedin",
        scraped_at=_NOW,
    )
    fp = compute_fingerprint(job.company, job.title, job.location)
    repo.save_job(
        job=job,
        fingerprint=fp,
        match_result=_match_result(),
        threshold=70,
        near_miss_floor=55,
        seen_at=_NOW,
    )
    jobs_before = repo.list_jobs()
    repo.close()

    # Reopen — later migrations already applied; jobs intact, new tables present + empty.
    repo2 = SQLiteJobRepository(db_path=db_path)
    assert "resumes" in _table_names(repo2._conn)
    assert "generations" in _table_names(repo2._conn)
    assert len(repo2.list_jobs()) == len(jobs_before) == 1
    resume_count = repo2._conn.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
    assert resume_count == 0
    versions = [
        row[0] for row in repo2._conn.execute("SELECT version FROM schema_migrations")
    ]
    assert versions == [1, 2, 3, 4, 5, 6]
    repo2.close()


def test_migrations_4_and_5_upgrade_existing_store_without_touching_jobs(tmp_path):
    """Opening a v1/v2/v3 store applies migrations 4 + 5 and preserves every job row."""
    db_path = str(tmp_path / "agent.db")

    # Build a database at migrations 1+2+3 only, with a real job row. Migration 5
    # alters the generations table, so both 4 and 5 must be withheld together.
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    for version, sql in MIGRATIONS:
        if version >= 4:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, _NOW.isoformat()),
        )
    conn.commit()
    conn.close()

    repo = SQLiteJobRepository(db_path=db_path)  # opening applies migrations 4 + 5
    job = Job(
        title="Senior Software Engineer",
        company="Acme Corp",
        location="Remote",
        url="https://example.com/1",
        description="A job.",
        platform="linkedin",
        scraped_at=_NOW,
    )
    fp = compute_fingerprint(job.company, job.title, job.location)
    repo.save_job(
        job=job,
        fingerprint=fp,
        match_result=_match_result(),
        threshold=70,
        near_miss_floor=55,
        seen_at=_NOW,
    )

    assert "generations" in _table_names(repo._conn)
    assert "status" in _generations_columns(repo._conn)
    assert len(repo.list_jobs()) == 1
    gen_count = repo._conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
    assert gen_count == 0
    versions = [
        row[0] for row in repo._conn.execute("SELECT version FROM schema_migrations")
    ]
    assert versions == [1, 2, 3, 4, 5, 6]
    repo.close()
