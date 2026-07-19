"""SQLiteGenerationRepository — the SQLite implementation of GenerationRepositoryPort.

Stores one row per generated document in the same ``data/agent.db`` file as the job
and resume stores (ADR-023/034 §3). Same construction pattern as
``SQLiteJobRepository`` — stdlib ``sqlite3``, WAL journal, a busy timeout, and short
per-operation commits. Only provenance is stored, never document content
(CLAUDE.md #2); ``review_locations`` is persisted as a JSON string and round-tripped
back to ``list[str]``.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime

from src.adapters.repository.migrations import apply_migrations
from src.core.domain.generation import Generation
from src.core.ports.generation_repository_port import GenerationRepositoryPort

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/agent.db"
_DEFAULT_BUSY_TIMEOUT_MS = 5000


class SQLiteGenerationRepository(GenerationRepositoryPort):
    """Persist generated-document records in a single SQLite database file."""

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
            "Generation repository ready at %s (busy_timeout=%dms)",
            db_path,
            busy_timeout_ms,
        )

    def save(self, generation: Generation) -> Generation:
        """Persist a generation record and return it."""
        self._conn.execute(
            "INSERT INTO generations ("
            "id, job_id, kind, outcome, file_path, provider, model, "
            "repair_note, review_locations, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                generation.id,
                generation.job_id,
                generation.kind,
                generation.outcome,
                generation.file_path,
                generation.provider,
                generation.model,
                generation.repair_note,
                json.dumps(generation.review_locations),
                generation.created_at.isoformat(),
            ),
        )
        self._conn.commit()
        logger.info(
            "Recorded %s generation %s for job %d (%s)",
            generation.kind,
            generation.id,
            generation.job_id,
            generation.outcome,
        )
        return generation

    def get(self, generation_id: str) -> Generation | None:
        """Return the generation with ``generation_id``, or None when absent."""
        row = self._conn.execute(
            "SELECT * FROM generations WHERE id = ?", (generation_id,)
        ).fetchone()
        return self._row_to_generation(row) if row is not None else None

    def list_for_job(self, job_id: int) -> list[Generation]:
        """Return every generation recorded for ``job_id``, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM generations WHERE job_id = ? ORDER BY created_at DESC",
            (job_id,),
        ).fetchall()
        return [self._row_to_generation(row) for row in rows]

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    @staticmethod
    def _row_to_generation(row: sqlite3.Row) -> Generation:
        """Map a ``generations`` row to a Generation entity."""
        return Generation(
            id=row["id"],
            job_id=row["job_id"],
            kind=row["kind"],
            outcome=row["outcome"],
            file_path=row["file_path"],
            provider=row["provider"],
            model=row["model"],
            repair_note=row["repair_note"],
            review_locations=json.loads(row["review_locations"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
