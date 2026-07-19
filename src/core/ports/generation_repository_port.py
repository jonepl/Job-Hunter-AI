"""GenerationRepositoryPort — abstract interface for generation-record storage (F).

Persists one ``Generation`` per generated document (provenance only — never the
content, CLAUDE.md #2). F owns the ``generations`` table (§15 gap 4/7). The core
sees only this port; it has no knowledge of SQLite (ADR-023). The port trades in
``Generation`` entities, never rows.
"""

from abc import ABC, abstractmethod

from src.core.domain.generation import Generation


class GenerationRepositoryPort(ABC):
    """Abstract base class defining the contract for generation-record persistence."""

    @abstractmethod
    def save(self, generation: Generation) -> Generation:
        """Persist a generation record and return it.

        Args:
            generation: The record to store (its ``id`` is the caller-assigned
                opaque identifier, also the ``.docx`` filename stem).

        Returns:
            The stored Generation.
        """
        ...

    @abstractmethod
    def update(self, generation: Generation) -> Generation:
        """Persist changes to an existing generation record and return it.

        Used by the async lifecycle (W6) to transition a ``pending`` row to
        ``ready``/``failed`` — updating status, outcome, file path, repair note,
        and review locations for the row with the matching ``id``.

        Args:
            generation: The record whose stored row (keyed by ``id``) to overwrite.

        Returns:
            The updated Generation.
        """
        ...

    @abstractmethod
    def get(self, generation_id: str) -> Generation | None:
        """Return the generation with ``generation_id``, or None when absent.

        Args:
            generation_id: The opaque identifier of the generation.

        Returns:
            The matching Generation, or None.
        """
        ...

    @abstractmethod
    def list_for_job(self, job_id: int) -> list[Generation]:
        """Return every generation recorded for ``job_id``, newest first.

        Args:
            job_id: The repository id of the job.

        Returns:
            The job's generations ordered newest first (possibly empty).
        """
        ...
