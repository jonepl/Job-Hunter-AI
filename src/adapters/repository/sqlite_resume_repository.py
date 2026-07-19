"""SQLiteResumeRepository — the SQLite implementation of ResumeRepositoryPort.

Stores the master resume with version history in the same ``data/agent.db`` file
as the job store (ADR-023/028). Same construction pattern as
``SQLiteJobRepository`` — stdlib ``sqlite3``, WAL journal, a busy timeout, and
short per-operation commits (ADR-034 §1). Two connections to the one WAL database
are safe; whichever repository opens first applies any pending migrations.

Exactly one row has ``is_active = 1`` at a time, enforced by a partial UNIQUE
index. Activation therefore clears the old active row and sets the new one in a
single transaction so the invariant never breaks mid-write.
"""

import logging
import os
import sqlite3
from datetime import datetime

from src.adapters.repository.migrations import apply_migrations
from src.core.domain.resume import Resume
from src.core.ports.resume_repository_port import ResumeRepositoryPort

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/agent.db"
_DEFAULT_BUSY_TIMEOUT_MS = 5000


class SQLiteResumeRepository(ResumeRepositoryPort):
    """Persist master-resume versions in a single SQLite database file."""

    def __init__(
        self,
        db_path: str = _DEFAULT_DB_PATH,
        busy_timeout_ms: int = _DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        """Open (creating if needed) the database and apply pending migrations.

        Args:
            db_path: Path to the SQLite file. Parent directories are created.
            busy_timeout_ms: ``PRAGMA busy_timeout`` in milliseconds — how long a
                writer waits for a competing writer before erroring (ADR-034 §1).
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
            "Resume repository ready at %s (busy_timeout=%dms)", db_path, busy_timeout_ms
        )

    def get_active(self) -> Resume | None:
        """Return the currently active resume version, or None when none stored."""
        row = self._conn.execute(
            "SELECT * FROM resumes WHERE is_active = 1"
        ).fetchone()
        return self._row_to_resume(row) if row is not None else None

    def save_version(self, resume: Resume) -> Resume:
        """Persist ``resume`` as the next version and make it the active one."""
        next_version = self._next_version()
        now_iso = datetime.now().isoformat()
        uploaded_iso = (resume.uploaded_at or datetime.now()).isoformat()

        # Deactivate the current active row, then insert the new active version —
        # committed together so the single-active invariant always holds.
        self._conn.execute("UPDATE resumes SET is_active = 0 WHERE is_active = 1")
        self._conn.execute(
            "INSERT INTO resumes ("
            "version, filename, content_hash, size_bytes, raw_text, "
            "skill_count, role_count, is_active, uploaded_at, parsed_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                next_version,
                resume.filename,
                resume.content_hash,
                resume.size_bytes,
                resume.raw_text,
                resume.skill_count,
                resume.role_count,
                uploaded_iso,
                resume.parsed_at.isoformat(),
            ),
        )
        self._conn.commit()
        logger.info("Stored master resume v%d (%s)", next_version, resume.filename)

        stored = self.get_active()
        assert stored is not None  # just inserted and activated
        return stored

    def list_versions(self) -> list[Resume]:
        """Return every stored resume version, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM resumes ORDER BY version DESC"
        ).fetchall()
        return [self._row_to_resume(row) for row in rows]

    def activate(self, version: int) -> bool:
        """Make an existing stored version the active one (restore)."""
        row = self._conn.execute(
            "SELECT id FROM resumes WHERE version = ?", (version,)
        ).fetchone()
        if row is None:
            return False
        self._conn.execute("UPDATE resumes SET is_active = 0 WHERE is_active = 1")
        self._conn.execute(
            "UPDATE resumes SET is_active = 1 WHERE version = ?", (version,)
        )
        self._conn.commit()
        logger.info("Activated master resume v%d", version)
        return True

    def find_by_hash(self, content_hash: str) -> Resume | None:
        """Return the stored version whose source bytes hash to ``content_hash``."""
        row = self._conn.execute(
            "SELECT * FROM resumes WHERE content_hash = ? ORDER BY version DESC LIMIT 1",
            (content_hash,),
        ).fetchone()
        return self._row_to_resume(row) if row is not None else None

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def _next_version(self) -> int:
        """Return the next version number (current max + 1, or 1 when empty)."""
        row = self._conn.execute("SELECT MAX(version) AS m FROM resumes").fetchone()
        return (row["m"] or 0) + 1

    @staticmethod
    def _row_to_resume(row: sqlite3.Row) -> Resume:
        """Map a ``resumes`` row to a Resume entity."""
        return Resume(
            raw_text=row["raw_text"],
            parsed_at=datetime.fromisoformat(row["parsed_at"]),
            version=row["version"],
            filename=row["filename"],
            size_bytes=row["size_bytes"],
            content_hash=row["content_hash"],
            skill_count=row["skill_count"],
            role_count=row["role_count"],
            is_active=bool(row["is_active"]),
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
        )
