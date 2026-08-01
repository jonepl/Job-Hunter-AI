"""Thread-safe SQLite connection sharing for the repository layer (ADR-034 §1).

The web app used to open **six** independent ``sqlite3`` connections to the one
``data/agent.db`` file (jobs, resume, generation, settings, profile, run). During
a web-triggered run the pipeline writes on the event-loop thread while the client
polls ``GET /runs/{id}`` and ``GET /jobs`` on uvicorn threadpool threads, and a
user action (``update_status``, ``update_settings``, …) can write from yet another
threadpool thread. Those connections all opened with ``check_same_thread=False``
and relied only on ``PRAGMA busy_timeout`` — but ``busy_timeout`` arbitrates lock
contention *between transactions*; it does **not** make a ``sqlite3.Connection``
safe for concurrent use by multiple OS threads, nor protect the shared WAL index
(``-shm``) across the several connections open on the same file. That race
corrupts the in-memory/WAL-index state and SQLite then raises ``file is not a
database`` on every connection until the process restarts (handoff: bug1).

The fix is two-fold:

1. **One shared connection per database file.** Every repository on a given file
   wraps the *same* :class:`LockedConnection` (cached by absolute path). Collapsing
   the six connections to one removes the cross-connection WAL-write contention
   that a per-file lock alone would otherwise turn into a deadlock (a writer on
   connection A holding the WAL write-lock across statements while a writer on
   connection B spins on it under the Python lock).
2. **A single lock serializes every access to that connection.** Every ``execute``
   / ``executescript`` / ``commit`` / ``close`` runs while holding the file's lock,
   so no two OS threads ever manipulate the connection concurrently. Because SQLite
   cursors fetch lazily, rows are also fetched **inside** the lock
   (:class:`_Result` buffers them eagerly) — locking only around ``execute`` would
   let the fetch step the statement outside the lock and leave the race intact.

Hold times stay tiny (short per-op commits already exist) and the 2 s poll cadence
makes contention negligible. ``busy_timeout`` is kept as belt-and-suspenders for a
genuinely separate OS process (which this in-process lock cannot reach).

``:memory:`` databases are **never** shared or cached: each ``sqlite3.connect``
call opens a private in-memory database, and the unit tests depend on that
isolation. They get their own connection and their own lock.
"""

import logging
import os
import sqlite3
import threading

from src.adapters.repository.migrations import apply_migrations
from src.core.exceptions import RepositoryError

logger = logging.getLogger(__name__)

# One re-entrant lock per physical database file (keyed by absolute path), shared
# by the one connection opened on it. Re-entrant so a thread already holding the
# lock can nest calls without deadlocking (same thread ⇒ no corruption).
_LOCKS: dict[str, threading.RLock] = {}

# The single shared LockedConnection per physical file, so all six repositories on
# one database use the same connection (not six). Evicted on close().
_CONNS: dict[str, "LockedConnection"] = {}

# Guards mutation of _LOCKS and _CONNS (connection creation/eviction).
_GUARD = threading.Lock()

# db_path values that must never be shared or cached — each open is a private DB.
_UNSHAREABLE = frozenset({"", ":memory:"})


def _lock_for(key: str) -> threading.RLock:
    """Return the shared lock for ``key`` (an absolute path), creating it once.

    Callers hold :data:`_GUARD`.
    """
    lock = _LOCKS.get(key)
    if lock is None:
        lock = threading.RLock()
        _LOCKS[key] = lock
    return lock


class _Result:
    """A buffered, cursor-like result whose rows were fetched under the lock.

    Exposes the small slice of the ``sqlite3.Cursor`` API the repositories use —
    ``fetchone``, ``fetchall``, iteration, ``lastrowid``, ``rowcount`` — over rows
    already materialized inside :meth:`LockedConnection.execute`, so no lazy step
    of the statement ever happens outside the lock.
    """

    def __init__(self, rows: list[sqlite3.Row], lastrowid: int | None, rowcount: int) -> None:
        """Store the eagerly fetched rows and the originating cursor metadata."""
        self._rows = rows
        self._index = 0
        self.lastrowid = lastrowid
        self.rowcount = rowcount

    def fetchone(self) -> sqlite3.Row | None:
        """Return the next buffered row, or None when the buffer is exhausted."""
        if self._index < len(self._rows):
            row = self._rows[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self) -> list[sqlite3.Row]:
        """Return all remaining buffered rows."""
        rows = self._rows[self._index :]
        self._index = len(self._rows)
        return rows

    def __iter__(self):
        """Iterate the remaining buffered rows (``for row in conn.execute(...)``)."""
        return iter(self.fetchall())


class LockedConnection:
    """A ``sqlite3.Connection`` wrapper that serializes every access behind a lock.

    Every operation that touches the underlying connection — statement execution
    (including its row fetch), ``executescript``, ``commit``, ``close`` — runs
    while holding the file's shared lock, so no two OS threads ever manipulate the
    connection concurrently.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        lock: threading.RLock,
        cache_key: str | None,
    ) -> None:
        """Wrap ``conn`` under ``lock``; ``cache_key`` is its :data:`_CONNS` key or None."""
        self._conn = conn
        self._lock = lock
        self._cache_key = cache_key

    def execute(self, sql: str, params: object = ()) -> _Result:
        """Run one statement and eagerly fetch its rows, all under the lock.

        Args:
            sql: The SQL statement to execute.
            params: Bound parameters (a sequence/mapping); defaults to no params.

        Returns:
            A :class:`_Result` buffering the fetched rows plus ``lastrowid`` /
            ``rowcount`` — for writes the row list is simply empty.

        Raises:
            RepositoryError: If the underlying ``sqlite3`` call fails, so no raw
                persistence type escapes the adapter (bug3). Chains the original.
        """
        with self._lock:
            try:
                cursor = self._conn.execute(sql, params)
                rows = cursor.fetchall()
            except sqlite3.Error as exc:
                raise RepositoryError("SQLite execute failed") from exc
            return _Result(rows, cursor.lastrowid, cursor.rowcount)

    def executescript(self, sql: str) -> None:
        """Run a multi-statement script under the lock (used by migrations).

        Raises:
            RepositoryError: If the script fails, chaining the original ``sqlite3``
                error (bug3).
        """
        with self._lock:
            try:
                self._conn.executescript(sql)
            except sqlite3.Error as exc:
                raise RepositoryError("SQLite executescript failed") from exc

    def commit(self) -> None:
        """Commit the current transaction under the lock.

        Raises:
            RepositoryError: If the commit fails, chaining the original ``sqlite3``
                error (bug3).
        """
        with self._lock:
            try:
                self._conn.commit()
            except sqlite3.Error as exc:
                raise RepositoryError("SQLite commit failed") from exc

    def close(self) -> None:
        """Close the underlying connection and evict it from the shared cache.

        Eviction lets a later ``open_connection`` on the same path reopen a fresh
        connection (the "close then reopen the same file" pattern the persistence
        tests rely on).
        """
        with self._lock:
            self._conn.close()
        if self._cache_key is not None:
            with _GUARD:
                if _CONNS.get(self._cache_key) is self:
                    del _CONNS[self._cache_key]


def _new_connection(db_path: str, busy_timeout_ms: int, cache_key: str | None) -> LockedConnection:
    """Open a raw WAL connection, migrate it, and wrap it in a LockedConnection.

    Raises:
        RepositoryError: If opening, configuring, or migrating the database fails
            (a corrupt/truncated file, disk full, permissions, a migration error).
            Translating here as well as in the runtime mutators means an open-time
            failure never escapes as a raw ``sqlite3`` traceback either (bug3).
    """
    lock = _lock_for(cache_key) if cache_key is not None else threading.RLock()
    try:
        raw = sqlite3.connect(db_path, check_same_thread=False)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA journal_mode=WAL")
        raw.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        raw.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        raise RepositoryError("SQLite connection open failed") from exc
    conn = LockedConnection(raw, lock, cache_key)
    apply_migrations(conn)  # already translates via LockedConnection.executescript
    return conn


def open_connection(db_path: str, busy_timeout_ms: int) -> LockedConnection:
    """Return the shared WAL connection for ``db_path``, guarded by its file lock.

    Centralizes the open sequence every repository used to inline (create the
    parent directory, connect with ``check_same_thread=False``, set the WAL /
    ``busy_timeout`` / ``foreign_keys`` pragmas, apply pending migrations) and —
    crucially — returns **one** connection per physical file so all six
    repositories share it rather than opening six connections to the same WAL
    index. The shared lock, not ``busy_timeout``, is what makes cross-thread access
    safe (see the module docstring). ``:memory:`` paths are never shared.

    Args:
        db_path: Path to the SQLite file. Parent directories are created.
        busy_timeout_ms: ``PRAGMA busy_timeout`` in milliseconds — belt-and-braces
            for a genuinely separate OS process.

    Returns:
        A ready :class:`LockedConnection` with its schema migrated.
    """
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    if db_path in _UNSHAREABLE:
        return _new_connection(db_path, busy_timeout_ms, cache_key=None)

    key = os.path.abspath(db_path)
    with _GUARD:
        conn = _CONNS.get(key)
        if conn is None:
            conn = _new_connection(db_path, busy_timeout_ms, cache_key=key)
            _CONNS[key] = conn
        return conn
