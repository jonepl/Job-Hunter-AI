"""ResumeRepositoryPort — abstract interface for durable master-resume storage.

The candidate's resume is parsed once and persisted with version history so runs
read the cache instead of re-parsing the PDF every time (ADR-028, resolving the
``docs/prd.md §12`` C1 divergence). The core sees only this port; it has no
knowledge of SQLite (ADR-023). The port trades in ``Resume`` entities, never rows.

Exactly one stored version is **active** at a time — the one runs read and the one
tailoring will consume. Uploading identical bytes re-activates the existing version
rather than storing a duplicate.
"""

from abc import ABC, abstractmethod

from src.core.domain.resume import Resume


class ResumeRepositoryPort(ABC):
    """Abstract base class defining the contract for resume persistence adapters."""

    @abstractmethod
    def get_active(self) -> Resume | None:
        """Return the currently active resume version, or None when none stored.

        This is what every run reads. None means the store is empty (a first run
        will auto-seed it from the mounted resume path).

        Returns:
            The active Resume, or None when no version has been stored yet.
        """
        ...

    @abstractmethod
    def save_version(self, resume: Resume) -> Resume:
        """Persist ``resume`` as a new version and make it the active one.

        The new version number is assigned by the adapter (previous max + 1),
        overriding any ``version`` on the input. Marking it active deactivates the
        previously active version in the same transaction so the single-active
        invariant always holds.

        Args:
            resume: The parsed resume to store (its ``version``/``is_active`` are
                assigned by the adapter).

        Returns:
            The stored Resume with its assigned ``version`` and ``is_active`` True.
        """
        ...

    @abstractmethod
    def list_versions(self) -> list[Resume]:
        """Return every stored resume version, newest first.

        Backs ``resume list`` (CLI) and the future provenance panel. Each Resume
        carries its provenance; ``is_active`` marks the current one.

        Returns:
            All stored versions ordered by version descending (possibly empty).
        """
        ...

    @abstractmethod
    def activate(self, version: int) -> bool:
        """Make an existing stored version the active one (restore).

        Deactivates the current active version and activates ``version`` in one
        transaction. A no-op returning True when ``version`` is already active.

        Args:
            version: The version number to activate.

        Returns:
            True when a version with that number exists (now active), else False.
        """
        ...

    @abstractmethod
    def find_by_hash(self, content_hash: str) -> Resume | None:
        """Return the stored version whose source bytes hash to ``content_hash``.

        Lets the service short-circuit a re-upload of identical bytes — reactivate
        the existing version rather than re-parse and duplicate it.

        Args:
            content_hash: The hex digest of the source file bytes.

        Returns:
            The matching Resume, or None when no version has that hash.
        """
        ...
