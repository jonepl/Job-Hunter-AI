"""JobRepositoryPort — abstract interface for durable job persistence.

The core sees only this port; it has no knowledge of SQLite (ADR-023). All
writes go through a single repository instance so concurrent writers (a
scheduled run and a browser mutation) are serialized safely (ADR-034 §1).
"""

from abc import ABC, abstractmethod
from datetime import datetime

from src.core.domain.fingerprint import Fingerprint
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.stored_job import StoredJob


class JobRepositoryPort(ABC):
    """Abstract base class defining the contract for job persistence adapters."""

    @abstractmethod
    def find_by_fingerprint(self, key: str) -> StoredJob | None:
        """Return the stored job whose canonical fingerprint equals ``key``.

        Used for the dedup lookup before evaluation. A hit lets the caller reuse
        the stored evaluation instead of paying the evaluator again.

        Args:
            key: The pipe-joined canonical fingerprint key.

        Returns:
            The matching StoredJob (with its ``match_result`` and ``seen_on``),
            or None when no job has that fingerprint.
        """
        ...

    @abstractmethod
    def find_near_misses(
        self, canon_company: str, canon_title: str, exclude_key: str | None = None
    ) -> list[StoredJob]:
        """Return stored jobs sharing company + title but differing in location.

        These are logged (never auto-merged) so a human can decide whether a
        location-only difference is genuinely the same job (ADR-024).

        Args:
            canon_company: Canonical company field to match exactly.
            canon_title: Canonical title field to match exactly.
            exclude_key: A fingerprint key to omit from the results (the job's
                own key), or None to omit nothing.

        Returns:
            A list of near-miss StoredJobs (possibly empty).
        """
        ...

    @abstractmethod
    def save_job(
        self,
        job: Job,
        fingerprint: Fingerprint,
        match_result: MatchResult | None,
        threshold: int | None,
        near_miss_floor: int | None,
        seen_at: datetime,
    ) -> StoredJob:
        """Persist a newly evaluated job and return it with its assigned id.

        The write is committed on its own (short per-job commit, ADR-034 §1) so
        it never holds a run-long transaction against a concurrent writer.

        Args:
            job: The scraped job (raw fields and representative platform/url).
            fingerprint: The computed fingerprint (canonical fields + version).
            match_result: The evaluation to store, or None if unevaluated.
            threshold: The score threshold used for this evaluation (ADR-033).
            near_miss_floor: ``threshold - NEAR_MISS_BAND`` (ADR-033).
            seen_at: The timestamp for the initial sighting.

        Returns:
            The persisted StoredJob, including its new id.
        """
        ...

    @abstractmethod
    def record_sighting(
        self, job_id: int, platform: str, url: str | None, seen_at: datetime
    ) -> None:
        """Record that ``job_id`` was seen on ``platform`` at ``seen_at``.

        Idempotent per (job, platform): re-seeing a job on the same platform
        updates the sighting rather than duplicating it, and refreshes the job's
        ``last_seen_at``.

        Args:
            job_id: The repository id of the job.
            platform: The platform the job was sighted on.
            url: The platform-specific URL, if known.
            seen_at: When the sighting occurred.
        """
        ...

    @abstractmethod
    def get_seen_on(self, job_id: int) -> list[str]:
        """Return the distinct platforms a job has been sighted on.

        Args:
            job_id: The repository id of the job.

        Returns:
            A sorted list of distinct platform names.
        """
        ...
