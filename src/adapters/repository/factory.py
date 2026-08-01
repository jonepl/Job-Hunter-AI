"""Factories for the SQLite repositories (job + resume + generation + settings + run)."""

import logging
import os

from src.adapters.repository.sqlite_generation_repository import (
    SQLiteGenerationRepository,
)
from src.adapters.repository.sqlite_profile_repository import SQLiteProfileRepository
from src.adapters.repository.sqlite_repository import SQLiteJobRepository
from src.adapters.repository.sqlite_resume_repository import SQLiteResumeRepository
from src.adapters.repository.sqlite_run_repository import SQLiteRunRepository
from src.adapters.repository.sqlite_settings_repository import SQLiteSettingsRepository
from src.core.ports.generation_repository_port import GenerationRepositoryPort
from src.core.ports.job_repository_port import JobRepositoryPort
from src.core.ports.profile_repository_port import ProfileRepositoryPort
from src.core.ports.resume_repository_port import ResumeRepositoryPort
from src.core.ports.run_repository_port import RunRepositoryPort
from src.core.ports.settings_repository_port import SettingsRepositoryPort

logger = logging.getLogger(__name__)

# One repository instance per database path, so every profile (and the API and
# scheduler) writes through a single JobRepositoryPort. The six repository types
# (jobs, resume, generation, settings, profile, run) now share **one** SQLite
# connection per file — ``connection.open_connection`` caches it by path — and a
# single per-file lock serializes every access to it across threads. That shared
# lock, NOT ``busy_timeout``, is what makes concurrent web reads/writes safe
# (ADR-034 §1, handoff bug1).
_REPOSITORIES: dict[str, JobRepositoryPort] = {}
_RESUME_REPOSITORIES: dict[str, ResumeRepositoryPort] = {}
_GENERATION_REPOSITORIES: dict[str, GenerationRepositoryPort] = {}
_SETTINGS_REPOSITORIES: dict[str, SettingsRepositoryPort] = {}
_PROFILE_REPOSITORIES: dict[str, ProfileRepositoryPort] = {}
_RUN_REPOSITORIES: dict[str, RunRepositoryPort] = {}


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


def build_generation_repository() -> GenerationRepositoryPort:
    """Build (or return the cached) SQLite generation repository (F, ADR-029).

    Reads the same ``DB_PATH`` / ``DB_BUSY_TIMEOUT_MS`` as the job repository — the
    generation records live in the same database file. Repeated calls for the same
    path return the same instance so writes route through one connection (ADR-034 §1).

    Returns:
        A ready SQLiteGenerationRepository with its schema migrated.
    """
    db_path = os.getenv("DB_PATH", "data/agent.db")
    if db_path not in _GENERATION_REPOSITORIES:
        busy_timeout_ms = int(os.getenv("DB_BUSY_TIMEOUT_MS", "5000"))
        _GENERATION_REPOSITORIES[db_path] = SQLiteGenerationRepository(
            db_path=db_path, busy_timeout_ms=busy_timeout_ms
        )
    return _GENERATION_REPOSITORIES[db_path]


def build_settings_repository() -> SettingsRepositoryPort:
    """Build (or return the cached) SQLite settings repository (W7, ADR-031).

    Reads the same ``DB_PATH`` / ``DB_BUSY_TIMEOUT_MS`` as the job repository — the
    settings live in the same database file. Repeated calls for the same path return
    the same instance so writes route through one connection (ADR-034 §1).

    Returns:
        A ready SQLiteSettingsRepository with its schema migrated.
    """
    db_path = os.getenv("DB_PATH", "data/agent.db")
    if db_path not in _SETTINGS_REPOSITORIES:
        busy_timeout_ms = int(os.getenv("DB_BUSY_TIMEOUT_MS", "5000"))
        _SETTINGS_REPOSITORIES[db_path] = SQLiteSettingsRepository(
            db_path=db_path, busy_timeout_ms=busy_timeout_ms
        )
    return _SETTINGS_REPOSITORIES[db_path]


def build_profile_repository() -> ProfileRepositoryPort:
    """Build (or return the cached) SQLite search-profile repository (W7, ADR-031).

    Reads the same ``DB_PATH`` / ``DB_BUSY_TIMEOUT_MS`` as the job repository — the
    profiles live in the same database file. Repeated calls for the same path return
    the same instance so writes route through one connection (ADR-034 §1).

    Returns:
        A ready SQLiteProfileRepository with its schema migrated.
    """
    db_path = os.getenv("DB_PATH", "data/agent.db")
    if db_path not in _PROFILE_REPOSITORIES:
        busy_timeout_ms = int(os.getenv("DB_BUSY_TIMEOUT_MS", "5000"))
        _PROFILE_REPOSITORIES[db_path] = SQLiteProfileRepository(
            db_path=db_path, busy_timeout_ms=busy_timeout_ms
        )
    return _PROFILE_REPOSITORIES[db_path]


def build_run_repository() -> RunRepositoryPort:
    """Build (or return the cached) SQLite run repository (W8).

    Reads the same ``DB_PATH`` / ``DB_BUSY_TIMEOUT_MS`` as the job repository — the
    run records live in the same database file. Repeated calls for the same path
    return the same instance so the ``POST /runs`` background task and the client
    poll operate over one connection (ADR-034 §1).

    Returns:
        A ready SQLiteRunRepository with its schema migrated.
    """
    db_path = os.getenv("DB_PATH", "data/agent.db")
    if db_path not in _RUN_REPOSITORIES:
        busy_timeout_ms = int(os.getenv("DB_BUSY_TIMEOUT_MS", "5000"))
        _RUN_REPOSITORIES[db_path] = SQLiteRunRepository(
            db_path=db_path, busy_timeout_ms=busy_timeout_ms
        )
    return _RUN_REPOSITORIES[db_path]
