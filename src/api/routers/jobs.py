"""Jobs router — read and lifecycle endpoints over the persisted job store.

Routes contain no business logic (ADR-026): they call the repository and shape
its entities into lean response models. The two ``PATCH`` routes are the web
app's first mutations, writing through the same ``JobRepositoryPort`` the CLI's
``mark`` command uses (ADR-025).
"""

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_repository
from src.api.schemas import JobDetail, JobSummary, SavedUpdate, StatusUpdate
from src.core.domain.job_status import JobStatus
from src.core.domain.stored_job import StoredJob
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


@router.get("/{job_id}", response_model=JobDetail)
def get_job(
    job_id: int,
    repository: JobRepositoryPort = Depends(get_repository),
) -> JobDetail:
    """Return the full detail fan-out for one job.

    Args:
        job_id: The repository id of the job.
        repository: The shared job repository (injected).

    Returns:
        The job's detail, including its score breakdown and status history.

    Raises:
        HTTPException: 404 when no job has that id.
    """
    job = _job_or_404(repository, job_id)
    return JobDetail.from_stored_job(job, repository.get_status_history(job_id))


@router.patch("/{job_id}/status", response_model=JobDetail)
def update_status(
    job_id: int,
    body: StatusUpdate,
    repository: JobRepositoryPort = Depends(get_repository),
) -> JobDetail:
    """Transition a job to a human-set status, appending a history row.

    A same-value write is an idempotent no-op (no history row) but still returns
    the current detail. Machine statuses are rejected by the request schema (422).

    Args:
        job_id: The repository id of the job.
        body: The target status and an optional note.
        repository: The shared job repository (injected).

    Returns:
        The job's refreshed detail after the write.

    Raises:
        HTTPException: 404 when no job has that id.
    """
    _job_or_404(repository, job_id)
    repository.set_status(job_id, JobStatus(body.status), note=body.note)
    return _fresh_detail(repository, job_id)


@router.patch("/{job_id}/saved", response_model=JobDetail)
def update_saved(
    job_id: int,
    body: SavedUpdate,
    repository: JobRepositoryPort = Depends(get_repository),
) -> JobDetail:
    """Set a job's ``saved`` bookmark (never writes history).

    Args:
        job_id: The repository id of the job.
        body: The bookmark value to set.
        repository: The shared job repository (injected).

    Returns:
        The job's refreshed detail after the write.

    Raises:
        HTTPException: 404 when no job has that id.
    """
    _job_or_404(repository, job_id)
    repository.set_saved(job_id, body.saved)
    return _fresh_detail(repository, job_id)


def _job_or_404(repository: JobRepositoryPort, job_id: int) -> StoredJob:
    """Return the job or raise a 404."""
    job = repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No job with id {job_id}")
    return job


def _fresh_detail(repository: JobRepositoryPort, job_id: int) -> JobDetail:
    """Re-read a job and its history into a JobDetail after a write."""
    job = _job_or_404(repository, job_id)
    return JobDetail.from_stored_job(job, repository.get_status_history(job_id))
