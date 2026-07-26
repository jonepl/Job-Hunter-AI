"""RunService — orchestrates a web-triggered pipeline run end to end (W8).

The browser "Run search now" button kicks the same multi-profile pipeline a scheduled
fire runs, but a run is far too slow to block an HTTP request. So this service splits
the work in two, mirroring the W6 generation flow:

* :meth:`start_run` validates preconditions **synchronously** (a run is not already in
  progress; at least one profile is configured), then creates and returns a ``running``
  :class:`RunRecord` immediately — the poll handle.
* :meth:`execute_run` runs in a background task: it applies the DB settings to the
  environment (ADR-035), re-reads the profiles (ADR-031), runs them all sequentially,
  aggregates a small **summary** (profiles run, jobs found, newly evaluated,
  qualifying), and updates the row to ``succeeded`` — or ``failed`` (type-name only)
  on an unrecoverable error. It **never raises**: a background task has no caller.

Only one run executes at a time — one SQLite writer, sequential (ADR-034 §1). A run
lost to a restart is detected lazily on read: :meth:`get_run` flips a ``running`` row
older than the timeout to ``failed`` so the poll self-heals. The record is summary
only; no job content ever reaches it (CLAUDE.md #2) — the pipeline writes jobs to the
``jobs`` store as always.
"""

import logging
import threading
from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from src.core.domain.run_record import RunRecord, RunTrigger
from src.core.domain.run_report import RunReport
from src.core.domain.search_profile import SearchProfile
from src.core.exceptions import NoProfilesError, RunInProgressError
from src.core.ports.run_repository_port import RunRepositoryPort
from src.core.services.job_search_service import JobSearchService
from src.core.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_DEFAULT_RUN_TIMEOUT_SECONDS = 1800.0


class RunService:
    """Coordinate the settings bridge, profile loading, the pipeline, and run storage."""

    # Class-level so the single-flight guard is shared no matter which RunService
    # instance holds it. This closes a cross-thread TOCTOU: the manual runs execute on
    # uvicorn's event loop while a scheduled fire runs on the APScheduler worker thread,
    # and both call the check-then-act ``start_run`` — without a shared lock both could
    # read ``active() is None`` and both start (per-profile-scheduling §Resolved #1).
    _guard = threading.Lock()

    def __init__(
        self,
        run_repo: RunRepositoryPort,
        settings_service: SettingsService,
        service_factory: Callable[[SearchProfile], JobSearchService],
        run_all_profiles: Callable[..., "object"],
        run_timeout_seconds: float = _DEFAULT_RUN_TIMEOUT_SECONDS,
    ) -> None:
        """Wire the storage, config, and pipeline the run coordinates.

        Args:
            run_repo: Persistence for run records.
            settings_service: The DB-backed config layer (env bridge + profiles).
            service_factory: Builds a JobSearchService per profile.
            run_all_profiles: The sequential multi-profile runner (returns the
                per-profile RunReports); injected to keep this service pure.
            run_timeout_seconds: How long a ``running`` row may live before
                :meth:`get_run` flips it to ``failed`` (a task lost to a restart).
        """
        self._run_repo = run_repo
        self._settings_service = settings_service
        self._service_factory = service_factory
        self._run_all_profiles = run_all_profiles
        self._run_timeout_seconds = run_timeout_seconds

    @property
    def settings_service(self) -> SettingsService:
        """The DB-backed config layer this run reads (shared with the scheduler).

        Exposed so the scheduler — which shares this exact RunService instance
        (per-profile-scheduling §Resolved #3) — can re-read the live profiles for its
        freshness check without building a second settings service.
        """
        return self._settings_service

    def start_run(self, profile_id: int | None = None, trigger: RunTrigger = "web") -> RunRecord:
        """Create and store a ``running`` record, or raise if a run can't start.

        Preconditions are checked **synchronously** so a user-fixable problem is a
        clear error at request time rather than a silently failed background task. The
        check + insert run under a shared class-level lock so a manual run and a
        scheduled fire on different threads can never both pass the single-flight
        check (per-profile-scheduling §Resolved #1–2).

        Args:
            profile_id: When set, validate and run only that one profile (manual
                "Run now" or a scheduled fire); when None, run every enabled profile.
            trigger: What started the run — ``web`` for manual/API, ``scheduled`` for
                a scheduler fire. Recorded on the row so the feed can label it.

        Returns:
            The persisted ``running`` RunRecord (the poll handle).

        Raises:
            RunInProgressError: When a run is already in progress.
            NoProfilesError: When no runnable profile matches (none configured, all
                paused, or the requested ``profile_id`` is missing/paused).
        """
        with self._guard:
            active = self._active_run()
            if active is not None:
                raise RunInProgressError(f"A run ({active.id}) is already in progress.")
            profiles = self._settings_service.list_profiles()
            if not profiles:
                raise NoProfilesError("No search profiles configured — add one in Settings first.")
            if profile_id is not None:
                # A single-profile run (manual "Run now" or a scheduled fire) validates
                # the profile exists and is enabled — deliberately NOT schedule_enabled,
                # so a manual run can fire an unscheduled profile (§Resolved #5).
                target = _find_profile(profiles, profile_id)
                if target is None or not getattr(target, "enabled", True):
                    raise NoProfilesError(
                        f"Profile {profile_id} is not available to run — "
                        "it may have been deleted or paused."
                    )
            # ``getattr`` keeps this robust for test doubles that model profiles as bare
            # strings; real SearchProfiles always carry ``enabled``.
            elif not any(getattr(p, "enabled", True) for p in profiles):
                raise NoProfilesError(
                    "All search profiles are paused — resume one in Settings first."
                )
            run = RunRecord(
                id=uuid4().hex,
                status="running",
                trigger=trigger,
                started_at=datetime.now(),
            )
            logger.info("Started run %s (trigger=%s, profile=%s)", run.id, trigger, profile_id)
            return self._run_repo.save(run)

    async def execute_run(self, run_id: str, profile_id: int | None = None) -> None:
        """Run the pipeline for ``run_id`` to completion, updating its row (W8 task).

        Applies the DB settings to the environment (ADR-035), re-reads the profiles
        (ADR-031), runs them (all, or just ``profile_id`` when set), aggregates a
        summary, and marks the row ``succeeded`` — or ``failed`` on an unrecoverable
        error. **Never raises** — a background task has no caller to catch it, and the
        failure is recorded on the row for the poll to report. Only the exception
        *type* is stored/logged; a raw message can carry scraped or model text
        (CLAUDE.md #2).

        Args:
            run_id: The id of the ``running`` row to fulfil.
            profile_id: When set, run only that one profile (mirrors ``start_run``);
                when None, run every enabled profile.
        """
        run = self._run_repo.get(run_id)
        if run is None or run.status != "running":
            return  # already terminal, timed out, or gone — nothing to do

        try:
            self._settings_service.apply_to_environment()
            profiles = self._settings_service.list_profiles()
            if profile_id is not None:
                profiles = [p for p in profiles if _profile_id_of(p) == profile_id]
            reports = await self._run_all_profiles(
                profiles, self._service_factory, self._settings_service
            )
        except Exception as exc:  # noqa: BLE001 — record failure, never crash the task
            logger.error("Run %s failed (%s)", run_id, type(exc).__name__)
            self._run_repo.update(
                run.model_copy(
                    update={
                        "status": "failed",
                        "error": type(exc).__name__,
                        "finished_at": datetime.now(),
                    }
                )
            )
            return

        summary = _summarize(reports)
        self._run_repo.update(
            run.model_copy(
                update={
                    "status": "succeeded",
                    "finished_at": datetime.now(),
                    **summary,
                }
            )
        )
        logger.info(
            "Run %s complete — %d profile(s), %d job(s), %d new, %d qualifying",
            run_id,
            summary["profiles_run"],
            summary["jobs_found"],
            summary["new_jobs"],
            summary["qualifying"],
        )

    def get_run(self, run_id: str) -> RunRecord | None:
        """Return a run, flipping a timed-out ``running`` row to ``failed`` (W8).

        The background task lives in-process, so a restart loses it and leaves the
        row ``running`` forever. Detecting that lazily on read (``started_at`` older
        than the timeout) means the poll self-heals to ``failed``.

        Args:
            run_id: The id to look up.

        Returns:
            The RunRecord (possibly just transitioned to ``failed``), or None.
        """
        return self._heal(self._run_repo.get(run_id))

    def recent_runs(self, limit: int = 20) -> list[RunRecord]:
        """Return the most recent runs, newest first, healing any timed-out row.

        Args:
            limit: Maximum number of runs to return.

        Returns:
            Up to ``limit`` runs ordered newest first (possibly empty).
        """
        return [self._heal(run) for run in self._run_repo.list_recent(limit)]

    def _active_run(self) -> RunRecord | None:
        """Return the in-progress run, or None — healing a timed-out row first."""
        return self._heal(self._run_repo.active())

    def _heal(self, run: RunRecord | None) -> RunRecord | None:
        """Flip a ``running`` row past its timeout to ``failed`` (self-healing read)."""
        if run is None or run.status != "running":
            return run
        age = (datetime.now() - run.started_at).total_seconds()
        if age <= self._run_timeout_seconds:
            return run
        logger.warning("Run %s timed out after %.0fs — marking failed", run.id, age)
        return self._run_repo.update(
            run.model_copy(
                update={
                    "status": "failed",
                    "error": "TimeoutError",
                    "finished_at": datetime.now(),
                }
            )
        )


def _profile_id_of(profile: object) -> object:
    """Return a profile's id, tolerating test doubles that lack the attribute."""
    return getattr(profile, "profile_id", None)


def _find_profile(profiles: list, profile_id: int) -> object | None:
    """Return the profile with ``profile_id`` from a loaded list, or None."""
    return next((p for p in profiles if _profile_id_of(p) == profile_id), None)


def _summarize(reports: list[RunReport]) -> dict[str, int]:
    """Aggregate per-profile reports into the run's summary counts."""
    return {
        "profiles_run": len(reports),
        "jobs_found": sum(r.total_evaluated for r in reports),
        "new_jobs": sum(r.newly_evaluated_count for r in reports),
        "qualifying": sum(len(r.qualifying_results) for r in reports),
    }
