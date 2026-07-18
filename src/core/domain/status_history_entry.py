"""StatusHistoryEntry domain entity — one row of a job's lifecycle audit trail.

Every status transition appends one of these (ADR-025). The detail screen renders
them as the job's action timeline; `from_status` is None for the creation row.
"""

from datetime import datetime

from pydantic import BaseModel

from src.core.domain.job_status import JobStatus


class StatusHistoryEntry(BaseModel):
    """A single append-only status transition for a job.

    The creation row has ``from_status`` None (there was no prior state); every
    later row records the state it moved from and to, an optional note, and when.
    """

    from_status: JobStatus | None = None
    """The state transitioned from, or None for the creation row."""

    to_status: JobStatus
    changed_at: datetime
    note: str | None = None
