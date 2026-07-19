"""Unit tests for SQLiteGenerationRepository over an in-memory store."""

from datetime import datetime

from src.adapters.repository.sqlite_generation_repository import (
    SQLiteGenerationRepository,
)
from src.core.domain.generation import Generation


def _repo() -> SQLiteGenerationRepository:
    """Return a generation repository over a fresh in-memory database with jobs seeded.

    The ``generations`` table has a foreign key to ``jobs``, so the referenced job
    rows must exist before a generation can be saved.
    """
    repo = SQLiteGenerationRepository(db_path=":memory:")
    for job_id in (7, 99):
        _seed_job(repo, job_id)
    return repo


def _seed_job(repo: SQLiteGenerationRepository, job_id: int) -> None:
    """Insert a minimal ``jobs`` row so a generation can reference it."""
    repo._conn.execute(
        "INSERT INTO jobs ("
        "id, fingerprint_version, canon_company, canon_title, canon_location, "
        "company, title, location, first_seen_at, last_seen_at"
        ") VALUES (?, 1, 'c', 't', 'l', 'Co', 'Title', 'Loc', ?, ?)",
        (job_id, "2026-07-18T09:00:00", "2026-07-18T09:00:00"),
    )
    repo._conn.commit()


def _generation(gen_id: str, job_id: int = 7, **overrides) -> Generation:
    """Return a Generation with sensible defaults and optional overrides."""
    fields = {
        "id": gen_id,
        "job_id": job_id,
        "kind": "resume",
        "outcome": "clean",
        "file_path": f"data/generations/{gen_id}.docx",
        "provider": "openai",
        "model": "gpt-4o",
        "created_at": datetime(2026, 7, 18, 9, 0, 0),
    }
    fields.update(overrides)
    return Generation(**fields)


def test_save_then_get_round_trips():
    """A saved generation is retrievable by id with its fields intact."""
    repo = _repo()
    repo.save(_generation("aaa", provider="anthropic", model="claude-sonnet-4-5"))

    fetched = repo.get("aaa")
    assert fetched is not None
    assert fetched.provider == "anthropic"
    assert fetched.model == "claude-sonnet-4-5"
    assert fetched.kind == "resume"


def test_get_missing_returns_none():
    """Fetching an unknown id returns None."""
    assert _repo().get("nope") is None


def test_review_locations_json_round_trip():
    """review_locations survives the JSON round-trip as a list of strings."""
    repo = _repo()
    repo.save(
        _generation(
            "bbb",
            outcome="needs_review",
            review_locations=["Summary", "Experience → bullet 2"],
        )
    )
    fetched = repo.get("bbb")
    assert fetched.review_locations == ["Summary", "Experience → bullet 2"]


def test_empty_review_locations_default():
    """A clean generation stores and returns an empty review-locations list."""
    repo = _repo()
    repo.save(_generation("ccc"))
    assert repo.get("ccc").review_locations == []


def test_list_for_job_returns_newest_first():
    """list_for_job returns every generation for a job, newest first."""
    repo = _repo()
    repo.save(_generation("old", created_at=datetime(2026, 7, 1, 8, 0, 0)))
    repo.save(_generation("new", created_at=datetime(2026, 7, 18, 8, 0, 0)))
    repo.save(_generation("other", job_id=99))

    ids = [g.id for g in repo.list_for_job(7)]
    assert ids == ["new", "old"]


def test_list_for_job_empty():
    """A job with no generations returns an empty list."""
    assert _repo().list_for_job(1) == []
