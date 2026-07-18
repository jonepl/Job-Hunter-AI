"""StoredJob domain entity — a persisted job row with its reused evaluation.

Returned by ``JobRepositoryPort`` lookups. On a dedup hit the service reuses the
stored ``match_result`` instead of paying the evaluator again, and reads
``seen_on`` to render the cross-provider "seen on" read model.
"""

from datetime import datetime

from pydantic import BaseModel

from src.core.domain.match_result import MatchResult


class StoredJob(BaseModel):
    """A job as persisted in the repository, with its stored evaluation.

    The evaluation (``match_result``, ``threshold``, ``near_miss_floor``) is
    stored on the job itself — dedup means one evaluation per job at single-user
    scale (ADR-033: the threshold is persisted per evaluation).
    """

    id: int
    """The repository primary key."""

    company: str
    title: str
    location: str
    url: str | None = None

    fingerprint: str | None = None
    """The canonical dedup key, or None when dedup is disabled for this job."""

    fingerprint_version: int
    canon_company: str
    canon_title: str
    canon_location: str

    match_result: MatchResult | None = None
    """The stored evaluation, reused on a dedup hit. None when not yet evaluated."""

    threshold: int | None = None
    """The score threshold in force when this job was evaluated (ADR-033)."""

    near_miss_floor: int | None = None
    """``threshold - NEAR_MISS_BAND`` at evaluation time (ADR-033)."""

    first_seen_at: datetime
    last_seen_at: datetime

    seen_on: list[str] = []
    """Distinct platforms this job has been sighted on (the "seen on" model)."""
