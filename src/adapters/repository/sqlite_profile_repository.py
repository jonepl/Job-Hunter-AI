"""SQLiteProfileRepository — the SQLite implementation of ProfileRepositoryPort.

Stores the search definitions the run pipeline iterates, in the same ``data/agent.db``
file as the job store (ADR-023/031). Same construction pattern as the other
repositories — stdlib ``sqlite3``, WAL journal, a busy timeout, short per-operation
commits (ADR-034 §1). The list-valued columns (``work_types``, ``active_scrapers``)
are persisted as JSON strings and round-tripped back into enum lists in the adapter.
The DB row ``id`` is surfaced as the entity's ``profile_id``.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime

from src.adapters.repository.migrations import apply_migrations
from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.domain.work_type import WorkType
from src.core.ports.profile_repository_port import ProfileRepositoryPort

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/agent.db"
_DEFAULT_BUSY_TIMEOUT_MS = 5000


class SQLiteProfileRepository(ProfileRepositoryPort):
    """Persist search profiles in a single SQLite database file."""

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
            "Profile repository ready at %s (busy_timeout=%dms)",
            db_path,
            busy_timeout_ms,
        )

    def list_profiles(self) -> list[SearchProfile]:
        """Return every stored profile ordered by position, then id."""
        rows = self._conn.execute(
            "SELECT * FROM search_profiles ORDER BY position, id"
        ).fetchall()
        return [self._row_to_profile(row) for row in rows]

    def get_profile(self, profile_id: int) -> SearchProfile | None:
        """Return the profile with ``profile_id``, or None when absent."""
        row = self._conn.execute(
            "SELECT * FROM search_profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        return self._row_to_profile(row) if row is not None else None

    def create_profile(self, profile: SearchProfile) -> SearchProfile:
        """Persist a new profile at the next position; return it with its id."""
        next_position = (
            self._conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM search_profiles"
            ).fetchone()[0]
        )
        cursor = self._conn.execute(
            "INSERT INTO search_profiles ("
            "name, query, location, work_types, date_posted, active_scrapers, "
            "score_threshold, top_results, enabled, position, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                profile.name,
                profile.query,
                profile.location,
                _dump_work_types(profile.work_types),
                profile.date_posted.value if profile.date_posted else None,
                _dump_scrapers(profile.active_scrapers),
                profile.score_threshold,
                profile.top_results,
                int(profile.enabled),
                next_position,
                datetime.now().isoformat(),
            ),
        )
        self._conn.commit()
        return profile.model_copy(update={"profile_id": cursor.lastrowid})

    def update_profile(self, profile: SearchProfile) -> SearchProfile:
        """Persist changes to the profile identified by ``profile.profile_id``.

        ``last_run_at`` / ``last_run_status`` are deliberately **not** written here —
        they are pipeline-owned (see :meth:`set_last_run`), so a user edit in Settings
        can never clobber run history.
        """
        self._conn.execute(
            "UPDATE search_profiles SET "
            "name = ?, query = ?, location = ?, work_types = ?, date_posted = ?, "
            "active_scrapers = ?, score_threshold = ?, top_results = ?, enabled = ? "
            "WHERE id = ?",
            (
                profile.name,
                profile.query,
                profile.location,
                _dump_work_types(profile.work_types),
                profile.date_posted.value if profile.date_posted else None,
                _dump_scrapers(profile.active_scrapers),
                profile.score_threshold,
                profile.top_results,
                int(profile.enabled),
                profile.profile_id,
            ),
        )
        self._conn.commit()
        return profile

    def set_last_run(self, profile_id: int, status: str, at: str) -> None:
        """Record this profile's most recent run outcome (pipeline-owned).

        A narrow, dedicated write — not a full ``update_profile`` round-trip — so a
        concurrent user edit in Settings can't race with the pipeline's write.

        Args:
            profile_id: The profile whose run metadata to update.
            status: ``running`` | ``succeeded`` | ``failed``.
            at: ISO-8601 timestamp of the run start.
        """
        self._conn.execute(
            "UPDATE search_profiles SET last_run_at = ?, last_run_status = ? "
            "WHERE id = ?",
            (at, status, profile_id),
        )
        self._conn.commit()

    def delete_profile(self, profile_id: int) -> None:
        """Remove the profile with ``profile_id`` (a no-op when absent)."""
        self._conn.execute(
            "DELETE FROM search_profiles WHERE id = ?", (profile_id,)
        )
        self._conn.commit()

    def count(self) -> int:
        """Return the number of stored profiles."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM search_profiles"
        ).fetchone()[0]

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> SearchProfile:
        """Map a ``search_profiles`` row to a SearchProfile entity."""
        work_types_raw = row["work_types"]
        date_posted_raw = row["date_posted"]
        return SearchProfile(
            profile_id=row["id"],
            name=row["name"],
            query=row["query"],
            location=row["location"],
            work_types=(
                [WorkType(v) for v in json.loads(work_types_raw)]
                if work_types_raw
                else None
            ),
            date_posted=DatePosted(date_posted_raw) if date_posted_raw else None,
            active_scrapers=[
                ScraperName(v) for v in json.loads(row["active_scrapers"])
            ],
            score_threshold=row["score_threshold"],
            top_results=row["top_results"],
            enabled=bool(row["enabled"]),
            last_run_at=row["last_run_at"],
            last_run_status=row["last_run_status"],
        )


def _dump_work_types(work_types: list[WorkType] | None) -> str | None:
    """Serialize a work-type list to JSON, or None when unset."""
    if work_types is None:
        return None
    return json.dumps([w.value for w in work_types])


def _dump_scrapers(scrapers: list[ScraperName]) -> str:
    """Serialize a scraper list to a JSON array of enum values."""
    return json.dumps([s.value for s in scrapers])
