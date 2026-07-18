"""Jobs router — read endpoints over the persisted job store.

Routes contain no business logic (ADR-026): they call the repository and shape
its entities into lean response models.
"""

from fastapi import APIRouter, Depends

from src.api.deps import get_repository
from src.api.schemas import JobSummary
from src.core.ports.job_repository_port import JobRepositoryPort

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSummary])
def list_jobs(
    repository: JobRepositoryPort = Depends(get_repository),
) -> list[JobSummary]:
    """List all persisted jobs, ranked strongest-match first.

    Args:
        repository: The shared job repository (injected).

    Returns:
        Every stored job as a lean card-shaped JobSummary.
    """
    return [JobSummary.from_stored_job(job) for job in repository.list_jobs()]
