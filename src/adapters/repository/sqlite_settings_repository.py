"""SQLiteSettingsRepository — the SQLite implementation of SettingsRepositoryPort.

Stores the global configuration and secret values as flat key/value rows in the same
``data/agent.db`` file as the job store (ADR-023/031). Same construction pattern as
the other repositories — stdlib ``sqlite3``, WAL journal, a busy timeout, and short
per-operation commits (ADR-034 §1).
"""

import logging
import os
import sqlite3
from datetime import datetime

from src.adapters.repository.migrations import apply_migrations
from src.core.ports.settings_repository_port import SettingsRepositoryPort

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/agent.db"
_DEFAULT_BUSY_TIMEOUT_MS = 5000


class SQLiteSettingsRepository(SettingsRepositoryPort):
    """Persist the key/value settings store in a single SQLite database file."""

    def __init__(
        self,
        db_path: str = _DEFAULT_DB_PATH,
        busy_timeout_ms: int = _DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        """Open (creating if needed) the database and apply pending migrations.

        Args:
            db_path: Path to the SQLite file. Parent directories are created.
            busy_timeout_ms: ``PRAGMA busy_timeout`` in milliseconds (ADR-034 §1).
        """
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        self._conn.execute("PRAGMA foreign_keys=ON")
        apply_migrations(self._conn)
        logger.info(
            "Settings repository ready at %s (busy_timeout=%dms)",
            db_path,
            busy_timeout_ms,
        )

    def get_all(self) -> dict[str, str]:
        """Return every stored setting as a ``{key: value}`` mapping."""
        rows = self._conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def get(self, key: str) -> str | None:
        """Return the value for ``key``, or None when it is not stored."""
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row is not None else None

    def set(self, key: str, value: str) -> None:
        """Insert or update ``key`` with ``value``."""
        self._conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, value, datetime.now().isoformat()),
        )
        self._conn.commit()

    def delete(self, key: str) -> None:
        """Remove ``key`` if present (a no-op when absent)."""
        self._conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
