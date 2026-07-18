"""Unit tests for the SQLite repository factory."""

import src.adapters.repository.factory as factory_module
from src.adapters.repository.factory import build_repository
from src.adapters.repository.sqlite_repository import SQLiteJobRepository
from src.core.ports.job_repository_port import JobRepositoryPort


def _clear_cache() -> None:
    """Reset the module-level repository singleton cache between tests."""
    factory_module._REPOSITORIES.clear()


def test_build_repository_returns_port(tmp_path, monkeypatch):
    """build_repository returns a SQLiteJobRepository implementing the port."""
    _clear_cache()
    monkeypatch.setenv("DB_PATH", str(tmp_path / "agent.db"))
    repo = build_repository()
    assert isinstance(repo, SQLiteJobRepository)
    assert isinstance(repo, JobRepositoryPort)


def test_build_repository_is_singleton_per_path(tmp_path, monkeypatch):
    """Repeated calls for the same path return the same instance (ADR-034 §1)."""
    _clear_cache()
    monkeypatch.setenv("DB_PATH", str(tmp_path / "agent.db"))
    assert build_repository() is build_repository()


def test_build_repository_honours_db_path(tmp_path, monkeypatch):
    """The configured DB_PATH is used to create the database file."""
    _clear_cache()
    db_path = tmp_path / "custom.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    build_repository()
    assert db_path.exists()
