"""Factories for the SQLite repositories (job + resume)."""

import logging
import os

from src.adapters.repository.sqlite_repository import SQLiteJobRepository
from src.adapters.repository.sqlite_resume_repository import SQLiteResumeRepository
from src.core.ports.job_repository_port import JobRepositoryPort
from src.core.ports.resume_repository_port import ResumeRepositoryPort

logger = logging.getLogger(__name__)

# One repository instance per database path, so every profile (and later the API
# and scheduler) writes through a single JobRepositoryPort — ADR-034 §1 routes
# all writes through one instance to serialize concurrent writers safely.
_REPOSITORIES: dict[str, JobRepositoryPort] = {}
_RESUME_REPOSITORIES: dict[str, ResumeRepositoryPort] = {}


def build_repository() -> JobRepositoryPort:
    """Build (or return the cached) SQLite job repository from env configuration.

    Reads ``DB_PATH`` (default ``data/agent.db``) and ``DB_BUSY_TIMEOUT_MS``
    (default ``5000``). Unlike the optional pre-filter, persistence is always on
    — it is the durable backbone every later story builds on (ADR-023). Repeated
    calls for the same path return the same instance (ADR-034 §1).

    Returns:
        A ready SQLiteJobRepository with its schema migrated.
    """
    db_path = os.getenv("DB_PATH", "data/agent.db")
    if db_path not in _REPOSITORIES:
        busy_timeout_ms = int(os.getenv("DB_BUSY_TIMEOUT_MS", "5000"))
        _REPOSITORIES[db_path] = SQLiteJobRepository(
            db_path=db_path, busy_timeout_ms=busy_timeout_ms
        )
    return _REPOSITORIES[db_path]


def build_resume_repository() -> ResumeRepositoryPort:
    """Build (or return the cached) SQLite resume repository (ADR-028).

    Reads the same ``DB_PATH`` / ``DB_BUSY_TIMEOUT_MS`` as the job repository — the
    master resume lives in the same database file. Repeated calls for the same path
    return the same instance so writes route through one connection (ADR-034 §1).

    Returns:
        A ready SQLiteResumeRepository with its schema migrated.
    """
    db_path = os.getenv("DB_PATH", "data/agent.db")
    if db_path not in _RESUME_REPOSITORIES:
        busy_timeout_ms = int(os.getenv("DB_BUSY_TIMEOUT_MS", "5000"))
        _RESUME_REPOSITORIES[db_path] = SQLiteResumeRepository(
            db_path=db_path, busy_timeout_ms=busy_timeout_ms
        )
    return _RESUME_REPOSITORIES[db_path]
