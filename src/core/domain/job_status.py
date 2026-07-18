"""JobStatus — the nine-state job lifecycle (ADR-025).

Transitions are permissive (any → any), recorded in an append-only history. The
one hard domain rule is that a **machine write never clobbers a human-set status**;
`is_human_set` is the classification both that rule and the pipeline's suppression
step read.
"""

from enum import Enum


class JobStatus(str, Enum):
    """The lifecycle state of a job.

    Machine-set states (`new`, `evaluated`, `pre_filtered`) are assigned by the
    pipeline and are never user-selectable. Human-set states are assigned via the
    `mark` command (or the web UI, later).
    """

    NEW = "new"
    EVALUATED = "evaluated"
    PRE_FILTERED = "pre_filtered"
    APPLIED = "applied"
    STARTED = "started"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    NOT_INTERESTED = "not_interested"


MACHINE_STATUSES: frozenset[JobStatus] = frozenset(
    {JobStatus.NEW, JobStatus.EVALUATED, JobStatus.PRE_FILTERED}
)
"""States the pipeline assigns — never user-selectable, never clobber a human state."""

HUMAN_STATUSES: frozenset[JobStatus] = frozenset(JobStatus) - MACHINE_STATUSES
"""States a person sets — a re-scrape must never overwrite these, and the pipeline
withholds them from future runs."""


def is_human_set(status: JobStatus) -> bool:
    """Return True when a status was set by a person rather than the machine.

    Args:
        status: The status to classify.

    Returns:
        True for the six human-set states, False for the three machine-set states.
    """
    return status in HUMAN_STATUSES
