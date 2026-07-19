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
from src.service_factory import build_generation_service, build_resume_service

# Built once and reused: the async generation flow schedules a background task that
# runs after the request returns, so the poll and the task must share one service
# instance (and its repository connection, ADR-034 §1).
_GENERATION_SERVICE: GenerationService | None = None


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
