"""SQLiteRunRepository — the SQLite implementation of RunRepositoryPort (W8).

Stores one row per web-triggered run in the same ``data/agent.db`` file as the job,
resume, and generation stores (ADR-023/034 §1). Same construction pattern as the
other SQLite repositories — stdlib ``sqlite3``, WAL journal, a busy timeout, and short
per-operation commits. Only a summary is stored, never job content (CLAUDE.md #2).
"""

import logging
import os
import sqlite3
from datetime import datetime

from src.adapters.repository.migrations import apply_migrations
from src.core.domain.run_record import RunRecord
from src.core.ports.run_repository_port import RunRepositoryPort

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/agent.db"
_DEFAULT_BUSY_TIMEOUT_MS = 5000


class SQLiteRunRepository(RunRepositoryPort):
    """Persist run-lifecycle records in a single SQLite database file."""

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
        logger.info("Run repository ready at %s (busy_timeout=%dms)", db_path, busy_timeout_ms)

    def save(self, run: RunRecord) -> RunRecord:
        """Persist a new run record and return it."""
        self._conn.execute(
            "INSERT INTO runs ("
            "id, status, trigger, profiles_run, jobs_found, new_jobs, "
            "qualifying, error, started_at, finished_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run.id,
                run.status,
                run.trigger,
                run.profiles_run,
                run.jobs_found,
                run.new_jobs,
                run.qualifying,
                run.error,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
            ),
        )
        self._conn.commit()
        logger.info("Recorded run %s (%s, %s)", run.id, run.trigger, run.status)
        return run

    def update(self, run: RunRecord) -> RunRecord:
        """Persist changes to an existing run row (keyed by ``id``)."""
        self._conn.execute(
            "UPDATE runs SET "
            "status = ?, profiles_run = ?, jobs_found = ?, new_jobs = ?, "
            "qualifying = ?, error = ?, finished_at = ? "
            "WHERE id = ?",
            (
                run.status,
                run.profiles_run,
                run.jobs_found,
                run.new_jobs,
                run.qualifying,
                run.error,
                run.finished_at.isoformat() if run.finished_at else None,
                run.id,
            ),
        )
        self._conn.commit()
        logger.info("Updated run %s → %s", run.id, run.status)
        return run

    def get(self, run_id: str) -> RunRecord | None:
        """Return the run with ``run_id``, or None when absent."""
        row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._row_to_run(row) if row is not None else None

    def list_recent(self, limit: int = 20) -> list[RunRecord]:
        """Return up to ``limit`` runs, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def active(self) -> RunRecord | None:
        """Return the single ``running`` run, or None when none is in progress."""
        row = self._conn.execute(
            "SELECT * FROM runs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return self._row_to_run(row) if row is not None else None

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> RunRecord:
        """Map a ``runs`` row to a RunRecord entity."""
        return RunRecord(
            id=row["id"],
            status=row["status"],
            trigger=row["trigger"],
            profiles_run=row["profiles_run"],
            jobs_found=row["jobs_found"],
            new_jobs=row["new_jobs"],
            qualifying=row["qualifying"],
            error=row["error"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=(
                datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None
            ),
        )
