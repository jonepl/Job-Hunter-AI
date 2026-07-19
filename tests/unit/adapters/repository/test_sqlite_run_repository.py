"""Unit tests for SQLiteRunRepository (W8).

Exercises the run-lifecycle store against an in-memory SQLite database: the
save → update round-trip, the single-flight ``active()`` guard, ``list_recent``
ordering, and the summary-count columns. No network, no real DB file.
"""

from datetime import datetime, timedelta

from src.adapters.repository.sqlite_run_repository import SQLiteRunRepository
from src.core.domain.run_record import RunRecord

_NOW = datetime(2026, 7, 19, 9, 0, 0)


def _repo() -> SQLiteRunRepository:
    """Return a run repository over a fresh in-memory database."""
    return SQLiteRunRepository(db_path=":memory:")


def _running(run_id: str, started_at: datetime = _NOW) -> RunRecord:
    """Build a minimal ``running`` run record."""
    return RunRecord(id=run_id, status="running", started_at=started_at)


def test_save_then_get_round_trips_a_running_run():
    """A saved running run reads back identically."""
    repo = _repo()
    repo.save(_running("abc"))

    got = repo.get("abc")
    assert got is not None
    assert got.id == "abc"
    assert got.status == "running"
    assert got.trigger == "web"
    assert got.finished_at is None


def test_get_unknown_id_returns_none():
    """An unknown id yields None, not an error."""
    assert _repo().get("missing") is None


def test_update_persists_terminal_status_and_summary():
    """Updating a run stores the succeeded status, summary counts, and finish time."""
    repo = _repo()
    repo.save(_running("abc"))

    finished = repo.update(
        _running("abc").model_copy(
            update={
                "status": "succeeded",
                "profiles_run": 2,
                "jobs_found": 40,
                "new_jobs": 12,
                "qualifying": 5,
                "finished_at": _NOW + timedelta(minutes=3),
            }
        )
    )

    assert finished.status == "succeeded"
    got = repo.get("abc")
    assert got.profiles_run == 2
    assert got.jobs_found == 40
    assert got.new_jobs == 12
    assert got.qualifying == 5
    assert got.finished_at == _NOW + timedelta(minutes=3)


def test_update_persists_failed_error_type_name():
    """A failed run stores the bare error type name (never a raw message)."""
    repo = _repo()
    repo.save(_running("abc"))
    repo.update(
        _running("abc").model_copy(
            update={"status": "failed", "error": "RuntimeError", "finished_at": _NOW}
        )
    )
    assert repo.get("abc").error == "RuntimeError"


def test_active_returns_only_the_running_run():
    """``active`` returns the running row and None once it is terminal."""
    repo = _repo()
    repo.save(_running("abc"))
    assert repo.active() is not None
    assert repo.active().id == "abc"

    repo.update(_running("abc").model_copy(update={"status": "succeeded"}))
    assert repo.active() is None


def test_list_recent_is_newest_first_and_limited():
    """``list_recent`` orders by start time descending and honors the limit."""
    repo = _repo()
    for i in range(3):
        run = _running(f"run{i}", started_at=_NOW + timedelta(minutes=i))
        # Older runs must be terminal so only the last is 'running' (single-flight).
        if i < 2:
            run = run.model_copy(update={"status": "succeeded"})
        repo.save(run)

    recent = repo.list_recent(limit=2)
    assert [r.id for r in recent] == ["run2", "run1"]
