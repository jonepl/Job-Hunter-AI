"""Mark execution for the Job Hunter AI Agent — the ``mark`` CLI backend.

Moves a stored job through its lifecycle (ADR-025): a human-set status change
and/or a ``saved`` bookmark toggle. Contains no CLI/argparse dependency and
accepts plain Python objects, so the future ``PATCH /jobs/{id}`` API path can
reuse this exact logic.
"""

import logging

from src.core.domain.job_status import JobStatus
from src.core.ports.job_repository_port import JobRepositoryPort

logger = logging.getLogger(__name__)


def run_mark(
    repository: JobRepositoryPort,
    job_id: int,
    status: JobStatus | None = None,
    note: str | None = None,
    saved: bool | None = None,
) -> tuple[str, int]:
    """Apply a status and/or save change to one job, returning a message + exit code.

    Args:
        repository: The persistence adapter to mutate through.
        job_id: The repository id of the job to mark.
        status: A human-set status to transition to, or None to leave unchanged.
        note: Optional note recorded on the status-history row.
        saved: True/False to set the bookmark, or None to leave it unchanged.

    Returns:
        A tuple of (human-readable message, process exit code). Exit code is 0 on
        success, 1 when the job does not exist, and 2 when nothing was requested.
    """
    if status is None and saved is None:
        return "Nothing to do: pass --status, --save, or --unsave.", 2

    job = repository.get_job(job_id)
    if job is None:
        return f"No job with id {job_id}.", 1

    changes: list[str] = []
    if status is not None:
        if repository.set_status(job_id, status, note=note):
            changes.append(f"status → {status.value}")
        else:
            changes.append(f"status already {status.value} (no change)")
    if saved is not None:
        repository.set_saved(job_id, saved)
        changes.append("saved" if saved else "unsaved")

    message = f'Job {job_id} "{job.title}" @ {job.company}: ' + ", ".join(changes)
    logger.info(message)
    return message, 0
