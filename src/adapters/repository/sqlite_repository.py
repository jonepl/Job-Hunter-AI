"""SQLiteJobRepository — the SQLite implementation of JobRepositoryPort.

Stdlib ``sqlite3``, no ORM, WAL journal mode, a single file at ``data/agent.db``
(ADR-023). Write contention with a concurrent scheduled run is handled explicitly
(ADR-034 §1): every connection sets ``busy_timeout``, and each write is committed
on its own rather than held in a run-long transaction. All writes go through one
repository instance.
"""

import logging
import sqlite3
from datetime import datetime

from src.adapters.repository.connection import open_connection
from src.core.domain.fingerprint import Fingerprint
from src.core.domain.job import Job
from src.core.domain.job_status import JobStatus, is_human_set
from src.core.domain.match_result import MatchResult
from src.core.domain.status_history_entry import StatusHistoryEntry
from src.core.domain.stored_job import StoredJob
from src.core.ports.job_repository_port import JobRepositoryPort

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/agent.db"
_DEFAULT_BUSY_TIMEOUT_MS = 5000


class SQLiteJobRepository(JobRepositoryPort):
    """Persist jobs and their sightings in a single SQLite database file."""

    def __init__(
        self,
        db_path: str = _DEFAULT_DB_PATH,
        busy_timeout_ms: int = _DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        """Open (creating if needed) the database and apply pending migrations.

        Args:
            db_path: Path to the SQLite file. Parent directories are created.
            busy_timeout_ms: ``PRAGMA busy_timeout`` in milliseconds — kept as
                belt-and-suspenders for a separate OS process (ADR-034 §1).
        """
        # The connection is shared across threads (the web app reads on threadpool
        # threads while a run writes on the event loop). Cross-thread safety comes
        # from the per-file lock inside open_connection — NOT from busy_timeout,
        # which only arbitrates between transactions (ADR-034 §1, handoff bug1).
        self._conn = open_connection(db_path, busy_timeout_ms)
        logger.info("Job repository ready at %s (busy_timeout=%dms)", db_path, busy_timeout_ms)

    def list_jobs(self) -> list[StoredJob]:
        """Return every stored job, ranked by score descending (unevaluated last).

        Uses a single grouped read of ``sightings`` to attach ``seen_on`` to every
        row, so listing N jobs costs two queries rather than N+1.
        """
        rows = self._conn.execute(
            "SELECT * FROM jobs "
            "ORDER BY overall_score IS NULL, overall_score DESC, last_seen_at DESC"
        ).fetchall()

        seen_on_by_job = self._seen_on_by_job()
        return [
            self._row_to_stored_job(row, seen_on=seen_on_by_job.get(row["id"], [])) for row in rows
        ]

    def get_job(self, job_id: int) -> StoredJob | None:
        """Return the stored job with the given id, or None when absent."""
        return self._get_by_id(job_id)

    def set_status(
        self,
        job_id: int,
        to_status: JobStatus,
        note: str | None = None,
        *,
        machine: bool = False,
    ) -> bool:
        """Transition a job to ``to_status`` with the ADR-025 guards."""
        row = self._conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return False

        current = JobStatus(row["status"])
        if to_status == current:
            return False  # idempotent no-op — no history row
        if machine and is_human_set(current):
            return False  # the machine never clobbers a human-set status

        now_iso = datetime.now().isoformat()
        self._conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (to_status.value, job_id))
        self._conn.execute(
            "INSERT INTO status_history "
            "(job_id, from_status, to_status, note, changed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (job_id, current.value, to_status.value, note, now_iso),
        )
        self._conn.commit()  # update + history commit together (ADR-034 §1)
        return True

    def set_saved(self, job_id: int, saved: bool) -> None:
        """Set the ``saved`` bookmark (idempotent, never writes history)."""
        self._conn.execute("UPDATE jobs SET saved = ? WHERE id = ?", (1 if saved else 0, job_id))
        self._conn.commit()

    def get_status_history(self, job_id: int) -> list[StatusHistoryEntry]:
        """Return a job's status history oldest-first (empty for an unknown job)."""
        rows = self._conn.execute(
            "SELECT from_status, to_status, note, changed_at FROM status_history "
            "WHERE job_id = ? ORDER BY id",
            (job_id,),
        ).fetchall()
        return [
            StatusHistoryEntry(
                from_status=JobStatus(row["from_status"]) if row["from_status"] else None,
                to_status=JobStatus(row["to_status"]),
                note=row["note"],
                changed_at=datetime.fromisoformat(row["changed_at"]),
            )
            for row in rows
        ]

    def find_by_fingerprint(self, key: str) -> StoredJob | None:
        """Return the stored job with the exact canonical fingerprint ``key``."""
        row = self._conn.execute("SELECT * FROM jobs WHERE fingerprint = ?", (key,)).fetchone()
        return self._row_to_stored_job(row) if row is not None else None

    def find_near_misses(
        self, canon_company: str, canon_title: str, exclude_key: str | None = None
    ) -> list[StoredJob]:
        """Return stored jobs with equal company + title but a different location."""
        sql = "SELECT * FROM jobs WHERE canon_company = ? AND canon_title = ?"
        params: list[object] = [canon_company, canon_title]
        if exclude_key is not None:
            sql += " AND (fingerprint IS NULL OR fingerprint != ?)"
            params.append(exclude_key)
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_stored_job(row) for row in rows]

    def save_job(
        self,
        job: Job,
        fingerprint: Fingerprint,
        match_result: MatchResult | None,
        threshold: int | None,
        near_miss_floor: int | None,
        seen_at: datetime,
    ) -> StoredJob:
        """Insert a newly evaluated job plus its first sighting, then return it."""
        now_iso = seen_at.isoformat()
        match_json = match_result.model_dump_json() if match_result is not None else None
        overall_score = match_result.score if match_result is not None else None
        # An evaluated job lands as ``evaluated``; an unevaluated one as ``new``.
        status = JobStatus.EVALUATED if match_result is not None else JobStatus.NEW

        cursor = self._conn.execute(
            "INSERT INTO jobs ("
            "fingerprint, fingerprint_version, canon_company, canon_title, "
            "canon_location, company, title, location, url, description, "
            "overall_score, threshold, near_miss_floor, match_result_json, "
            "status, salary_min, salary_max, salary_currency, salary_period, "
            "employment_type, posted_at, first_seen_at, last_seen_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fingerprint.key,
                fingerprint.version,
                fingerprint.canon_company,
                fingerprint.canon_title,
                fingerprint.canon_location,
                job.company,
                job.title,
                job.location,
                job.url,
                job.description,
                overall_score,
                threshold,
                near_miss_floor,
                match_json,
                status.value,
                job.salary_min,
                job.salary_max,
                job.salary_currency,
                job.salary_period,
                job.employment_type,
                job.posted_at.isoformat() if job.posted_at is not None else None,
                now_iso,
                now_iso,
            ),
        )
        job_id = int(cursor.lastrowid)
        # Creation history row (from NULL → initial status) keeps the audit
        # trail complete, committed with the insert (ADR-034 §1).
        self._conn.execute(
            "INSERT INTO status_history "
            "(job_id, from_status, to_status, note, changed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (job_id, None, status.value, None, now_iso),
        )
        self._conn.commit()  # short per-job commit (ADR-034 §1)

        self.record_sighting(job_id, job.platform, job.url, seen_at)
        stored = self._get_by_id(job_id)
        assert stored is not None  # just inserted
        return stored

    def record_sighting(
        self, job_id: int, platform: str, url: str | None, seen_at: datetime
    ) -> None:
        """Upsert a sighting for (job, platform) and refresh ``last_seen_at``."""
        now_iso = seen_at.isoformat()
        self._conn.execute(
            "INSERT INTO sightings (job_id, platform, url, seen_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT (job_id, platform) DO UPDATE SET "
            "seen_at = excluded.seen_at, url = excluded.url",
            (job_id, platform, url, now_iso),
        )
        self._conn.execute("UPDATE jobs SET last_seen_at = ? WHERE id = ?", (now_iso, job_id))
        self._conn.commit()

    def get_seen_on(self, job_id: int) -> list[str]:
        """Return the sorted distinct platforms a job has been sighted on."""
        rows = self._conn.execute(
            "SELECT DISTINCT platform FROM sightings WHERE job_id = ? ORDER BY platform",
            (job_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def _get_by_id(self, job_id: int) -> StoredJob | None:
        """Return the stored job with the given primary key, or None."""
        row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_stored_job(row) if row is not None else None

    def _seen_on_by_job(self) -> dict[int, list[str]]:
        """Return a map of job id → its sorted distinct sighting platforms.

        One grouped query for the whole table, used by ``list_jobs`` to avoid a
        per-row ``get_seen_on`` call.
        """
        rows = self._conn.execute(
            "SELECT DISTINCT job_id, platform FROM sightings ORDER BY job_id, platform"
        ).fetchall()
        result: dict[int, list[str]] = {}
        for row in rows:
            result.setdefault(row["job_id"], []).append(row["platform"])
        return result

    def _row_to_stored_job(self, row: sqlite3.Row, seen_on: list[str] | None = None) -> StoredJob:
        """Map a ``jobs`` row (with its sightings) to a StoredJob entity.

        Args:
            row: A ``jobs`` table row.
            seen_on: Pre-fetched sighting platforms for this job. When None (the
                single-row callers), they are fetched with a per-row query.
        """
        if seen_on is None:
            seen_on = self.get_seen_on(row["id"])
        match_result = (
            MatchResult.model_validate_json(row["match_result_json"])
            if row["match_result_json"]
            else None
        )
        return StoredJob(
            id=row["id"],
            company=row["company"],
            title=row["title"],
            location=row["location"],
            url=row["url"],
            description=row["description"],
            fingerprint=row["fingerprint"],
            fingerprint_version=row["fingerprint_version"],
            canon_company=row["canon_company"],
            canon_title=row["canon_title"],
            canon_location=row["canon_location"],
            match_result=match_result,
            threshold=row["threshold"],
            near_miss_floor=row["near_miss_floor"],
            status=JobStatus(row["status"]),
            saved=bool(row["saved"]),
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            salary_currency=row["salary_currency"],
            salary_period=row["salary_period"],
            employment_type=row["employment_type"],
            posted_at=(datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None),
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            seen_on=seen_on,
        )
