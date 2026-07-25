"""FastAPI dependency providers.

The API is a driving adapter beside the CLI (ADR-026): it reuses the same
core/repository and adds no business logic. Read endpoints need only the shared
job repository, so they depend on ``build_repository()`` directly — not
``service_factory.build_service()``, which requires a SearchProfile and builds
scrapers/evaluator/email for the run pipeline (far heavier than a read needs).
"""

from src.adapters.repository.factory import build_repository
from src.core.ports.job_repository_port import JobRepositoryPort
from src.core.services.generation_service import GenerationService
from src.core.services.resume_service import ResumeService
from src.core.services.run_service import RunService
from src.core.services.settings_service import SettingsService
from src.orchestration.service_factory import (
    build_generation_service,
    build_resume_service,
    build_run_service,
    build_settings_service,
)

# Built once and reused: the async generation flow schedules a background task that
# runs after the request returns, so the poll and the task must share one service
# instance (and its repository connection, ADR-034 §1).
_GENERATION_SERVICE: GenerationService | None = None
_SETTINGS_SERVICE: SettingsService | None = None
_RUN_SERVICE: RunService | None = None


def get_repository() -> JobRepositoryPort:
    """Return the shared job repository (a per-DB_PATH singleton).

    Returns:
        The process-wide JobRepositoryPort instance.
    """
    return build_repository()


def get_resume_service() -> ResumeService:
    """Return the shared ResumeService (the same one the CLI drives, ADR-028).

    Returns:
        A ResumeService over the format-sniffing parser and the singleton resume
        repository.
    """
    return build_resume_service()


def get_generation_service() -> GenerationService:
    """Return the shared GenerationService (the same one the CLI drives, W6/ADR-029).

    Cached at module scope so a scheduled background generation task and the client
    poll operate on one instance over one DB connection.

    Returns:
        The process-wide GenerationService instance.
    """
    global _GENERATION_SERVICE
    if _GENERATION_SERVICE is None:
        _GENERATION_SERVICE = build_generation_service()
    return _GENERATION_SERVICE


def get_settings_service() -> SettingsService:
    """Return the shared SettingsService (the DB-backed config layer, W7/ADR-031).

    Cached at module scope so the Settings routes operate over one repository
    connection (ADR-034 §1).

    Returns:
        The process-wide SettingsService instance.
    """
    global _SETTINGS_SERVICE
    if _SETTINGS_SERVICE is None:
        _SETTINGS_SERVICE = build_settings_service()
    return _SETTINGS_SERVICE


def get_run_service() -> RunService:
    """Return the shared RunService (the web "Run search now" flow, W8).

    Cached at module scope so the ``POST /runs`` background task and the client poll
    operate on one instance over one repository connection (ADR-034 §1).

    Returns:
        The process-wide RunService instance.
    """
    global _RUN_SERVICE
    if _RUN_SERVICE is None:
        _RUN_SERVICE = build_run_service()
    return _RUN_SERVICE
