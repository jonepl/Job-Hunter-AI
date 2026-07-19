"""RunRepositoryPort — abstract interface for run-lifecycle storage (W8).

Persists one ``RunRecord`` per web-triggered pipeline run (summary + lifecycle,
never job content — CLAUDE.md #2). The core sees only this port; it has no knowledge
of SQLite (ADR-023). The port trades in ``RunRecord`` entities, never rows.
"""

from abc import ABC, abstractmethod

from src.core.domain.run_record import RunRecord


class RunRepositoryPort(ABC):
    """Abstract base class defining the contract for run-record persistence."""

    @abstractmethod
    def save(self, run: RunRecord) -> RunRecord:
        """Persist a new run record and return it.

        Args:
            run: The record to store (its ``id`` is the caller-assigned poll handle).

        Returns:
            The stored RunRecord.
        """
        ...

    @abstractmethod
    def update(self, run: RunRecord) -> RunRecord:
        """Persist changes to an existing run row (keyed by ``id``) and return it.

        Used to transition a ``running`` row to ``succeeded``/``failed`` — updating
        status, the summary counts, the error, and ``finished_at``.

        Args:
            run: The record whose stored row to overwrite.

        Returns:
            The updated RunRecord.
        """
        ...

    @abstractmethod
    def get(self, run_id: str) -> RunRecord | None:
        """Return the run with ``run_id``, or None when absent.

        Args:
            run_id: The opaque identifier of the run.

        Returns:
            The matching RunRecord, or None.
        """
        ...

    @abstractmethod
    def list_recent(self, limit: int = 20) -> list[RunRecord]:
        """Return the most recent runs, newest first.

        Args:
            limit: Maximum number of runs to return.

        Returns:
            Up to ``limit`` runs ordered newest first (possibly empty).
        """
        ...

    @abstractmethod
    def active(self) -> RunRecord | None:
        """Return the single ``running`` run, or None when no run is in progress.

        The single-flight guard: only one run may execute at a time (one SQLite
        writer, ADR-034 §1), so at most one row is ever ``running``.

        Returns:
            The in-progress RunRecord, or None.
        """
        ...
