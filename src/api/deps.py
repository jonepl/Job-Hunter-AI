"""FastAPI dependency providers.

The API is a driving adapter beside the CLI (ADR-026): it reuses the same
core/repository and adds no business logic. Read endpoints need only the shared
job repository, so they depend on ``build_repository()`` directly — not
``service_factory.build_service()``, which requires a SearchProfile and builds
scrapers/evaluator/email for the run pipeline (far heavier than a read needs).
"""

from src.adapters.repository.factory import build_repository
from src.core.ports.job_repository_port import JobRepositoryPort


def get_repository() -> JobRepositoryPort:
    """Return the shared job repository (a per-DB_PATH singleton).

    Returns:
        The process-wide JobRepositoryPort instance.
    """
    return build_repository()
