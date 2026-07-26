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


def _running(run_id: str, started_at: datetime = _NOW, profile_id: int | None = None) -> RunRecord:
    """Build a minimal ``running`` run record."""
    return RunRecord(id=run_id, status="running", started_at=started_at, profile_id=profile_id)


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


def test_save_round_trips_profile_id():
    """A per-profile run's ``profile_id`` survives the round-trip; a batch stays None."""
    repo = _repo()
    repo.save(_running("scoped", profile_id=7))
    repo.save(_running("batch", started_at=_NOW + timedelta(minutes=1)))

    assert repo.get("scoped").profile_id == 7
    assert repo.get("batch").profile_id is None


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


def test_list_recent_filters_by_profile_id_excluding_global_batches():
    """A ``profile_id`` filter returns only that profile's runs, never NULL batches."""
    repo = _repo()
    # A global batch, a run for profile 5, and a run for profile 9 — all terminal but the
    # last so the single-flight invariant (one running row) holds.
    repo.save(_running("batch").model_copy(update={"status": "succeeded"}))
    repo.save(
        _running("p5", started_at=_NOW + timedelta(minutes=1), profile_id=5).model_copy(
            update={"status": "succeeded"}
        )
    )
    repo.save(_running("p9", started_at=_NOW + timedelta(minutes=2), profile_id=9))

    scoped = repo.list_recent(profile_id=5)
    assert [r.id for r in scoped] == ["p5"]

    # No filter still returns everything, newest first.
    assert [r.id for r in repo.list_recent()] == ["p9", "p5", "batch"]
