"""Unit tests for SQLiteSettingsRepository over an in-memory store (W7)."""

from src.adapters.repository.sqlite_settings_repository import (
    SQLiteSettingsRepository,
)


def _repo() -> SQLiteSettingsRepository:
    """Return a settings repository over a fresh in-memory database."""
    return SQLiteSettingsRepository(db_path=":memory:")


def test_set_then_get_round_trips():
    """A stored value is retrievable by key."""
    repo = _repo()
    repo.set("evaluator_provider", "anthropic")
    assert repo.get("evaluator_provider") == "anthropic"


def test_get_missing_returns_none():
    """An unknown key returns None."""
    assert _repo().get("nope") is None


def test_set_updates_existing_key():
    """Setting an existing key overwrites its value (upsert)."""
    repo = _repo()
    repo.set("voice_tone", "direct")
    repo.set("voice_tone", "warm")
    assert repo.get("voice_tone") == "warm"


def test_get_all_returns_every_pair():
    """get_all returns the full key/value mapping."""
    repo = _repo()
    repo.set("a", "1")
    repo.set("b", "2")
    assert repo.get_all() == {"a": "1", "b": "2"}


def test_delete_removes_a_key():
    """delete removes a key; deleting an absent key is a no-op."""
    repo = _repo()
    repo.set("openai_api_key", "sk-x")
    repo.delete("openai_api_key")
    assert repo.get("openai_api_key") is None
    repo.delete("openai_api_key")  # no error on a second delete
