"""SettingsRepositoryPort — abstract interface for the key/value settings store (W7).

Persists the global operational configuration and secret values as flat key/value
pairs (ADR-031). ``.env`` seeds this store on first run; thereafter it is
authoritative. The core sees only this port; it has no knowledge of SQLite (ADR-023).
"""

from abc import ABC, abstractmethod


class SettingsRepositoryPort(ABC):
    """Abstract base class defining the contract for key/value settings persistence."""

    @abstractmethod
    def get_all(self) -> dict[str, str]:
        """Return every stored setting as a ``{key: value}`` mapping (possibly empty)."""
        ...

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Return the value for ``key``, or None when it is not stored."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Insert or update ``key`` with ``value``."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove ``key`` if present (a no-op when absent)."""
        ...
