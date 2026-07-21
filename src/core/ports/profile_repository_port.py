"""ProfileRepositoryPort — abstract interface for search-profile storage (W7).

Persists the search definitions the run pipeline iterates (ADR-031). Replaces the
``PROFILE_N_`` env-loading path at run time; the store is seeded from ``.env`` on
first run. The port trades in ``SearchProfile`` entities, never rows; the core has
no knowledge of SQLite (ADR-023).
"""

from abc import ABC, abstractmethod

from src.core.domain.search_profile import SearchProfile


class ProfileRepositoryPort(ABC):
    """Abstract base class defining the contract for search-profile persistence."""

    @abstractmethod
    def list_profiles(self) -> list[SearchProfile]:
        """Return every stored profile ordered by position (possibly empty)."""
        ...

    @abstractmethod
    def get_profile(self, profile_id: int) -> SearchProfile | None:
        """Return the profile with ``profile_id``, or None when absent."""
        ...

    @abstractmethod
    def create_profile(self, profile: SearchProfile) -> SearchProfile:
        """Persist a new profile and return it with its assigned id and position."""
        ...

    @abstractmethod
    def update_profile(self, profile: SearchProfile) -> SearchProfile:
        """Persist changes to the profile identified by ``profile.profile_id``."""
        ...

    @abstractmethod
    def delete_profile(self, profile_id: int) -> None:
        """Remove the profile with ``profile_id`` (a no-op when absent)."""
        ...

    @abstractmethod
    def set_last_run(self, profile_id: int, status: str, at: str) -> None:
        """Record this profile's most recent run outcome (pipeline-owned).

        A narrow write, separate from :meth:`update_profile`, so the run pipeline's
        last-run metadata can never be clobbered by a concurrent user edit.

        Args:
            profile_id: The profile whose run metadata to update.
            status: ``running`` | ``succeeded`` | ``failed``.
            at: ISO-8601 timestamp of the run start.
        """
        ...

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored profiles."""
        ...
