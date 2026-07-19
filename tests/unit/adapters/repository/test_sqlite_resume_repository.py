"""Unit tests for SQLiteResumeRepository.

Exercised against a real in-memory SQLite connection (our own store), never a
mock — no real user files or network.
"""

from datetime import datetime

from src.adapters.repository.sqlite_resume_repository import SQLiteResumeRepository
from src.core.domain.resume import Resume

_NOW = datetime(2026, 7, 18, 9, 0, 0)


def _repo() -> SQLiteResumeRepository:
    """Return a fresh in-memory resume repository."""
    return SQLiteResumeRepository(db_path=":memory:")


def _resume(
    raw_text: str = "corpus text",
    content_hash: str = "hash-a",
    filename: str = "resume.pdf",
    size_bytes: int = 1000,
    skill_count: int = 5,
    role_count: int = 2,
) -> Resume:
    """Return a parsed Resume with overridable provenance (pre-storage)."""
    return Resume(
        raw_text=raw_text,
        parsed_at=_NOW,
        filename=filename,
        content_hash=content_hash,
        size_bytes=size_bytes,
        skill_count=skill_count,
        role_count=role_count,
        uploaded_at=_NOW,
    )


def test_get_active_empty_store_returns_none():
    """An empty store has no active version."""
    assert _repo().get_active() is None


def test_list_versions_empty_store_returns_empty_list():
    """An empty store lists no versions."""
    assert _repo().list_versions() == []


def test_save_version_assigns_v1_and_activates():
    """The first stored version is v1, active, with its provenance preserved."""
    repo = _repo()
    stored = repo.save_version(_resume(filename="me.pdf", skill_count=7))

    assert stored.version == 1
    assert stored.is_active is True
    assert stored.filename == "me.pdf"
    assert stored.skill_count == 7
    assert repo.get_active().version == 1


def test_save_version_increments_and_switches_active():
    """A second save is v2, active, and demotes v1 (single-active invariant)."""
    repo = _repo()
    repo.save_version(_resume(content_hash="hash-a"))
    v2 = repo.save_version(_resume(content_hash="hash-b", raw_text="newer"))

    assert v2.version == 2
    assert v2.is_active is True
    active = repo.get_active()
    assert active.version == 2
    assert active.raw_text == "newer"

    versions = repo.list_versions()
    assert [r.version for r in versions] == [2, 1]  # newest first
    assert [r.is_active for r in versions] == [True, False]


def test_activate_restores_a_prior_version():
    """Activating an older version demotes the current active one."""
    repo = _repo()
    repo.save_version(_resume(content_hash="hash-a"))
    repo.save_version(_resume(content_hash="hash-b"))

    assert repo.activate(1) is True
    assert repo.get_active().version == 1
    # Exactly one active version at a time.
    assert sum(1 for r in repo.list_versions() if r.is_active) == 1


def test_activate_missing_version_returns_false():
    """Activating a non-existent version is a no-op returning False."""
    repo = _repo()
    repo.save_version(_resume())
    assert repo.activate(99) is False
    assert repo.get_active().version == 1


def test_find_by_hash_matches_stored_bytes():
    """A stored version is retrievable by its content hash; misses return None."""
    repo = _repo()
    repo.save_version(_resume(content_hash="hash-a"))
    found = repo.find_by_hash("hash-a")
    assert found is not None
    assert found.content_hash == "hash-a"
    assert repo.find_by_hash("nope") is None
