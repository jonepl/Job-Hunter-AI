"""Concurrency regression tests for the shared SQLite connection guard (bug1).

These reproduce the ``file is not a database`` fingerprint from the defect log:
during a web-triggered run the pipeline writes on one thread while the client
polls reads on other threads, all over connections to the same ``data/agent.db``
file. ``PRAGMA busy_timeout`` alone does not make that safe; the per-file lock in
``connection.open_connection`` does. Without the lock these tests raise
``sqlite3.DatabaseError`` (``file is not a database`` / SQLITE_MISUSE) fairly
quickly; with it they stay clean.

File-backed ``tmp_path`` databases are used (not ``:memory:``) so WAL is real and
several repositories genuinely share one ``-shm`` index — the resource the bug
corrupts. Each ``:memory:`` connection would otherwise get its own private DB.
"""

import sqlite3
import threading
from datetime import datetime

import pytest

from src.adapters.repository.connection import open_connection
from src.adapters.repository.sqlite_repository import SQLiteJobRepository
from src.adapters.repository.sqlite_run_repository import SQLiteRunRepository
from src.core.domain.fingerprint import compute_fingerprint
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.run_record import RunRecord
from src.core.exceptions import RepositoryError

_NOW = datetime(2026, 7, 14, 9, 0, 0)


def _job(seq: int) -> Job:
    """Return a Job with a unique identity per ``seq`` (so every save is a new row)."""
    return Job(
        title=f"Senior Software Engineer {seq}",
        company=f"Acme {seq}",
        location="Remote",
        url=f"https://linkedin.com/jobs/{seq}",
        description="A job.",
        platform="linkedin",
        scraped_at=_NOW,
    )


def _match_result(job: Job, score: int = 82) -> MatchResult:
    """Return a minimal well-formed MatchResult for ``job``."""

    def _cat(mx: int) -> ScoreCategory:
        return ScoreCategory(max=mx, earned=mx, reasoning="ok")

    return MatchResult(
        job=job,
        score=score,
        seniority_level="Senior",
        years_experience_detected=8,
        hire_recommendation="Yes",
        score_breakdown=ScoreBreakdown(
            role_alignment=_cat(20),
            technical_stack_match=_cat(15),
            system_design_architecture=_cat(15),
            impact_and_metrics=_cat(15),
            domain_industry_experience=_cat(10),
            problem_space_relevance=_cat(10),
            ownership_and_leadership=_cat(10),
            resume_signal_quality=_cat(3),
            career_trajectory=_cat(2),
        ),
        matched_skills=["python"],
        missing_skills=[],
        summary="Strong fit.",
    )


def _save(repo: SQLiteJobRepository, seq: int) -> None:
    """Persist a fresh evaluated job (write path the pipeline exercises)."""
    job = _job(seq)
    fp = compute_fingerprint(job.company, job.title, job.location)
    repo.save_job(
        job=job,
        fingerprint=fp,
        match_result=_match_result(job),
        threshold=75,
        near_miss_floor=60,
        seen_at=_NOW,
    )


def _run_workers(targets: list, per_worker: int) -> list[BaseException]:
    """Run each callable in ``targets`` for ``per_worker`` iterations concurrently.

    Args:
        targets: One callable per worker thread; each takes the iteration index.
        per_worker: How many times each worker invokes its callable.

    Returns:
        Every exception raised by any worker (empty when all stayed clean).
    """
    errors: list[BaseException] = []
    errors_lock = threading.Lock()
    start = threading.Event()

    def _worker(target) -> None:
        start.wait()
        for i in range(per_worker):
            try:
                target(i)
            except BaseException as exc:  # noqa: BLE001 — the test records any failure
                with errors_lock:
                    errors.append(exc)
                return

    threads = [threading.Thread(target=_worker, args=(t,)) for t in targets]
    for thread in threads:
        thread.start()
    start.set()  # release all workers together to maximize contention
    for thread in threads:
        thread.join()
    return errors


def test_concurrent_reads_during_writes_do_not_corrupt_connection(tmp_path):
    """Four readers hammering ``list_jobs`` while a writer saves must never raise.

    This is the unit-level repro of the incident: the poll (``GET /jobs`` →
    ``list_jobs``) and the run (``save_job``) hit the one shared connection from
    different threads. The per-file lock keeps SQLite's WAL index intact.
    """
    db_path = str(tmp_path / "agent.db")
    repo = SQLiteJobRepository(db_path=db_path)

    def _reader(_i: int) -> None:
        repo.list_jobs()

    def _writer(i: int) -> None:
        _save(repo, i)

    errors = _run_workers([_reader, _reader, _reader, _reader, _writer], per_worker=40)
    repo.close()

    assert errors == [], f"concurrent access raised: {errors!r}"


def test_writers_across_repo_types_share_one_file_lock(tmp_path):
    """Two different repositories on the same file must serialize against each other.

    The lock is per *file*, not per repository — the jobs writer and the run-record
    writer open separate connections to the one ``agent.db`` and share its ``-shm``.
    Concurrent writes from both must complete without a ``DatabaseError``.
    """
    db_path = str(tmp_path / "agent.db")
    job_repo = SQLiteJobRepository(db_path=db_path)
    run_repo = SQLiteRunRepository(db_path=db_path)

    def _job_writer(i: int) -> None:
        _save(job_repo, i)

    def _run_writer(i: int) -> None:
        run_repo.save(
            RunRecord(
                id=f"run-{threading.get_ident()}-{i}",
                status="running",
                trigger="web",
                started_at=_NOW,
            )
        )

    errors = _run_workers([_job_writer, _run_writer], per_worker=40)
    job_repo.close()
    run_repo.close()

    assert errors == [], f"cross-repository writes raised: {errors!r}"
    assert not any(isinstance(e, sqlite3.DatabaseError) for e in errors)


# ---------------------------------------------------------------------------
# Boundary translation — sqlite3.Error → RepositoryError (bug3)
# ---------------------------------------------------------------------------


def test_execute_translates_sqlite_error_to_repository_error(tmp_path):
    """A failing statement surfaces as RepositoryError, never a raw sqlite3 type.

    Guards the ports boundary: a use-time failure (here, a missing table) is caught
    at the shared connection seam and re-raised as the technology-agnostic domain
    error, with the original ``sqlite3.Error`` preserved on ``__cause__`` for the
    server-side log.
    """
    conn = open_connection(str(tmp_path / "agent.db"), busy_timeout_ms=5000)
    try:
        with pytest.raises(RepositoryError) as excinfo:
            conn.execute("SELECT * FROM table_that_does_not_exist")
    finally:
        conn.close()

    assert isinstance(excinfo.value.__cause__, sqlite3.Error)


def test_open_connection_translates_corrupt_file_at_open_time(tmp_path):
    """Opening a non-database file surfaces as RepositoryError, not a raw traceback.

    The open path (connect + pragmas + migrations) is a different call path than the
    runtime mutators, so it is wrapped too — a corrupt/truncated file, a permissions
    error, or a migration failure never escapes as a bare ``sqlite3`` error either.
    """
    corrupt = tmp_path / "agent.db"
    corrupt.write_bytes(b"this is definitely not a sqlite database header")

    with pytest.raises(RepositoryError) as excinfo:
        open_connection(str(corrupt), busy_timeout_ms=5000)

    assert isinstance(excinfo.value.__cause__, sqlite3.Error)
