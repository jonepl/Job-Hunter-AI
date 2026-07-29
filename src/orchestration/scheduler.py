"""Scheduler — APScheduler-based in-process per-profile job scheduler.

Each ``SearchProfile`` owns its own schedule; the ``SchedulerManager`` keeps **one
APScheduler job per scheduled profile** (``profile-run-{id}``), each firing a single-
profile run on its own cron through the shared, guarded ``RunService`` lifecycle the
manual runs use (per-profile-scheduling feature). The scheduler runs in the same
process as uvicorn (ADR-032), so a profile edit reschedules it by a direct method call.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

import pytz
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.domain.run_report import RunReport
from src.core.domain.search_profile import SearchProfile
from src.core.exceptions import ModelNotFoundError, NoProfilesError, RunInProgressError
from src.core.services.settings_service import SettingsService
from src.infra.cost_estimator import estimate_run_cost
from src.infra.cost_tracker import CostTracker
from src.infra.pricing import rates_for, show_cost_estimate

if TYPE_CHECKING:
    from src.core.services.run_service import RunService

logger = logging.getLogger(__name__)

_DEFAULT_MISFIRE_GRACE_SECONDS = 3600


def _record_last_run(
    settings_service: SettingsService | None, profile_id: int, status: str
) -> None:
    """Stamp a profile's last-run status when a settings service is available (Part B)."""
    if settings_service is not None:
        settings_service.set_profile_last_run(profile_id, status, datetime.now().isoformat())


async def run_all_profiles(
    profiles: list[SearchProfile],
    service_factory: callable,
    settings_service: SettingsService | None = None,
) -> tuple[list[RunReport], list[tuple[int, str]]]:
    """Run all enabled search profiles sequentially.

    Each profile gets its own JobSearchService instance and delivers
    its own RunReport. Paused profiles (``enabled`` is False) are skipped.

    Args:
        profiles: List of SearchProfile instances to run.
        service_factory: Callable that accepts a SearchProfile and returns
                         a configured JobSearchService.
        settings_service: Optional DB-backed settings service; when provided, each
            profile's last-run status is stamped ``running`` → ``succeeded``/``failed``.

    Returns:
        A ``(reports, failures)`` tuple. ``reports`` holds the RunReport for each
        profile that completed; ``failures`` holds ``(profile_id, error_type_name)``
        for each profile whose pipeline raised. Batch-resilience is unchanged — a
        transient failure is recorded and the run continues; a fatal
        ``ModelNotFoundError`` is recorded and aborts the remaining profiles. The
        caller (``RunService.execute_run``) derives the run status from ``failures``
        so a failed run is never reported as a clean success (Bug 2).
    """
    enabled = [p for p in profiles if p.enabled]
    skipped = len(profiles) - len(enabled)
    if skipped:
        logger.info("Skipping %d paused profile(s)", skipped)
    logger.info("Scheduler — starting run for %d profile(s)", len(enabled))

    reports: list[RunReport] = []
    failures: list[tuple[int, str]] = []

    # Load cost tracking config once per scheduled run
    show_cost = show_cost_estimate()
    provider = os.getenv("EVALUATOR_PROVIDER", "").lower()
    input_rate, output_rate = rates_for(provider)

    for profile in enabled:
        logger.info(
            "Running profile %d: %s | %s",
            profile.profile_id,
            profile.query,
            profile.location,
        )

        if show_cost:
            estimate = estimate_run_cost(
                profile=profile,
                provider=provider,
                input_cost_per_1m=input_rate,
                output_cost_per_1m=output_rate,
            )
            logger.info("=" * 60)
            logger.info("Cost Estimate — Profile %d", profile.profile_id)
            logger.info("Max jobs to evaluate : %d", estimate.max_jobs)
            logger.info("Est. cost range      : %s", estimate.formatted_range)
            logger.info("=" * 60)
            cost_tracker = CostTracker(
                provider=provider,
                input_cost_per_1m=input_rate,
                output_cost_per_1m=output_rate,
                enabled=True,
            )
        else:
            estimate = None
            cost_tracker = CostTracker(
                provider=provider,
                input_cost_per_1m=input_rate,
                output_cost_per_1m=output_rate,
                enabled=False,
            )

        _record_last_run(settings_service, profile.profile_id, "running")

        try:
            service = service_factory(profile)
            report = await service.run(
                query=profile.query,
                location=profile.location,
                threshold=profile.score_threshold,
                top_results=profile.top_results,
                work_types=profile.work_types,
                date_posted=profile.date_posted,
                active_scrapers=profile.active_scrapers,
                cost_tracker=cost_tracker,
            )

            # Attach pre-run estimate to report
            report.cost_estimate = estimate
            reports.append(report)
            _record_last_run(settings_service, profile.profile_id, "succeeded")

            if show_cost and report.run_cost:
                logger.info("=" * 60)
                logger.info("Actual LLM Cost — Profile %d", profile.profile_id)
                logger.info("Jobs evaluated  : %d", report.run_cost.jobs_evaluated)
                logger.info(
                    "Total tokens    : %d in / %d out",
                    report.run_cost.total_input_tokens,
                    report.run_cost.total_output_tokens,
                )
                logger.info("Actual LLM cost : %s", report.run_cost.formatted_total)
                logger.info("=" * 60)

        except ModelNotFoundError as exc:
            # Fatal config shared by every profile — abort this trigger instead
            # of failing each profile identically. The daemon stays up so the
            # next trigger can pick up a corrected .env. Recorded as a failure so
            # a single-profile run hitting it terminates as ``failed`` (Bug 2).
            _record_last_run(settings_service, profile.profile_id, "failed")
            failures.append((profile.profile_id, "ModelNotFoundError"))
            logger.critical("%s", exc)
            logger.critical("Aborting this scheduled run; fix EVALUATOR_MODEL and restart.")
            break
        except Exception as e:
            _record_last_run(settings_service, profile.profile_id, "failed")
            failures.append((profile.profile_id, type(e).__name__))
            logger.error("Profile %d failed: %s", profile.profile_id, type(e).__name__)
            continue

    logger.info("Scheduler — all profiles complete")
    return reports, failures


def _misfire_grace_seconds() -> int:
    """Read the (generous) misfire grace period from ``.env``.

    APScheduler's default is **1 s**: if the scheduler loop is briefly delayed while
    the single worker is busy on a long run, an overlapping fire would be *silently
    skipped*. A generous window (default 1 hour) keeps ``coalesce`` collapsing a
    backlog into one fire instead of dropping it (per-profile-scheduling residual risks).
    """
    try:
        return int(
            os.getenv("SCHEDULER_MISFIRE_GRACE_SECONDS", str(_DEFAULT_MISFIRE_GRACE_SECONDS))
        )
    except ValueError:
        return _DEFAULT_MISFIRE_GRACE_SECONDS


def _job_id(profile_id: int) -> str:
    """The APScheduler job id for a profile's schedule."""
    return f"{SchedulerManager._JOB_PREFIX}{profile_id}"


def _profile_id_from_job_id(job_id: str) -> int | None:
    """Parse a profile id back out of a ``profile-run-{id}`` job id, or None."""
    if not job_id.startswith(SchedulerManager._JOB_PREFIX):
        return None
    try:
        return int(job_id[len(SchedulerManager._JOB_PREFIX) :])
    except ValueError:
        return None


class SchedulerManager:
    """The in-process ``BackgroundScheduler`` the web server owns, one job per profile.

    ADR-032: uvicorn runs in the foreground and the scheduler runs in the **same
    process** as a ``BackgroundScheduler``, so a profile edit in the Settings screen
    reconciles the jobs by a direct :meth:`sync` call — no cross-process signalling, DB
    polling, or container restart. This is the **only** scheduler; the CLI
    (``python -m src.main``) has no scheduled mode and always runs once and exits.

    **Sequential-run guarantee (two layers).** The ``BackgroundScheduler`` uses a
    single-worker ``ThreadPoolExecutor`` so two profiles scheduled at the same instant
    queue and serialize rather than flooding the scrapers/LLM concurrently. The shared
    ``RunService`` single-flight guard is the second layer — it also covers scheduled-
    vs-manual, since a manual run executes on uvicorn's loop, not the scheduler's
    executor (per-profile-scheduling §Key constraint).
    """

    _JOB_PREFIX = "profile-run-"

    def __init__(self, run_service: "RunService") -> None:
        """Create an unstarted manager bound to the shared RunService.

        Args:
            run_service: The **same** RunService instance the API's ``POST /runs`` uses
                (injected by the lifespan), so scheduled and manual runs share one
                single-flight guard (per-profile-scheduling §Resolved #3).
        """
        self._run_service = run_service
        self._scheduler: BackgroundScheduler | None = None

    @property
    def running(self) -> bool:
        """Whether the underlying scheduler is started."""
        return self._scheduler is not None and self._scheduler.running

    def start(self) -> None:
        """Start an empty scheduler configured for serialized, single-worker runs.

        Registers no jobs — call :meth:`sync` with the current profiles to populate it.
        Idempotent: a second call while running is a no-op.
        """
        if self.running:
            return
        self._scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=1)},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": _misfire_grace_seconds(),
            },
        )
        self._scheduler.start()
        logger.info("In-process scheduler started (per-profile jobs)")

    def sync(self, profiles: list[SearchProfile]) -> None:
        """Reconcile the scheduled jobs to match the given profiles (idempotent).

        Adds/reschedules a ``profile-run-{id}`` job for every profile that is
        ``enabled AND schedule_enabled`` with a non-empty cron; removes the jobs of
        profiles that are now unscheduled, paused, or deleted. Safe to call after any
        profile CRUD. A no-op when the scheduler has not been started.

        Args:
            profiles: The current set of profiles to reconcile against.
        """
        if self._scheduler is None:
            return

        wanted = {
            p.profile_id: p
            for p in profiles
            if p.enabled and p.schedule_enabled and p.schedule_cron
        }

        # Remove jobs whose profile is no longer scheduled (or was deleted).
        for job in self._scheduler.get_jobs():
            pid = _profile_id_from_job_id(job.id)
            if pid is not None and pid not in wanted:
                self._scheduler.remove_job(job.id)
                logger.info("Unscheduled profile %d", pid)

        # Add or re-point a job for every wanted profile.
        for pid, profile in wanted.items():
            try:
                tz = pytz.timezone(profile.schedule_timezone)
                trigger = CronTrigger.from_crontab(profile.schedule_cron, timezone=tz)
            except Exception as exc:  # noqa: BLE001 — a bad cron/tz skips one job, not all
                logger.warning(
                    "Skipping schedule for profile %d — invalid cron/timezone: %s", pid, exc
                )
                continue
            self._scheduler.add_job(
                self._fire,
                trigger,
                id=_job_id(pid),
                args=[pid],
                replace_existing=True,
            )
            logger.info(
                "Scheduled profile %d — cron: %s | timezone: %s",
                pid,
                profile.schedule_cron,
                profile.schedule_timezone,
            )

    def _fire(self, profile_id: int) -> None:
        """The per-profile job callback — run one profile through the guarded lifecycle.

        Re-checks the profile is still scheduled (guarding the tiny race where it is
        unscheduled between :meth:`sync` and this fire), then routes through the shared
        ``RunService`` guard. A blocked fire (a run already in progress, or the profile
        gone/paused) is logged once at INFO and skipped — never an error that would
        leave the trigger in a bad state (per-profile-scheduling §Resolved #5).

        Args:
            profile_id: The profile whose single-profile run to start.
        """
        if not self._profile_still_scheduled(profile_id):
            logger.info("Scheduled fire for profile %d skipped — no longer scheduled", profile_id)
            return
        try:
            run = self._run_service.start_run(profile_id=profile_id, trigger="scheduled")
        except (RunInProgressError, NoProfilesError) as exc:
            logger.info("Scheduled run skipped for profile %d: %s", profile_id, exc)
            return
        asyncio.run(self._run_service.execute_run(run.id, profile_id=profile_id))

    def _profile_still_scheduled(self, profile_id: int) -> bool:
        """Return whether ``profile_id`` is still enabled + schedule_enabled (fresh read)."""
        for profile in self._run_service.settings_service.list_profiles():
            if profile.profile_id == profile_id:
                return bool(profile.enabled and profile.schedule_enabled and profile.schedule_cron)
        return False

    def shutdown(self) -> None:
        """Stop the scheduler (on app/process shutdown). Idempotent."""
        if self._scheduler is not None and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("In-process scheduler stopped")
        self._scheduler = None


_MANAGER: "SchedulerManager | None" = None


def get_scheduler_manager() -> "SchedulerManager | None":
    """Return the process-wide scheduler manager, or None when none is running."""
    return _MANAGER


def set_scheduler_manager(manager: "SchedulerManager | None") -> None:
    """Set or clear the process-wide scheduler manager (owned by the API lifespan)."""
    global _MANAGER
    _MANAGER = manager
