"""Scheduler — APScheduler-based in-process job scheduler for multi-profile runs."""

import asyncio
import logging
import os

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.domain.search_profile import SearchProfile
from src.core.exceptions import ModelNotFoundError
from src.infra.cost_estimator import estimate_run_cost
from src.infra.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


async def run_all_profiles(
    profiles: list[SearchProfile],
    service_factory: callable,
) -> None:
    """Run all search profiles sequentially.

    Each profile gets its own JobSearchService instance and delivers
    its own RunReport.

    Args:
        profiles: List of SearchProfile instances to run.
        service_factory: Callable that accepts a SearchProfile and returns
                         a configured JobSearchService.
    """
    logger.info("Scheduler — starting run for %d profile(s)", len(profiles))

    # Load cost tracking config once per scheduled run
    show_cost = os.getenv("SHOW_COST_ESTIMATE", "false").lower() == "true"
    provider = os.getenv("EVALUATOR_PROVIDER", "").lower()

    if provider == "openai":
        input_rate = float(os.getenv("OPENAI_INPUT_COST_PER_1M", "2.50"))
        output_rate = float(os.getenv("OPENAI_OUTPUT_COST_PER_1M", "10.00"))
    else:
        input_rate = float(os.getenv("ANTHROPIC_INPUT_COST_PER_1M", "3.00"))
        output_rate = float(os.getenv("ANTHROPIC_OUTPUT_COST_PER_1M", "15.00"))

    for profile in profiles:
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
            # next trigger can pick up a corrected .env.
            logger.critical("%s", exc)
            logger.critical("Aborting this scheduled run; fix EVALUATOR_MODEL and restart.")
            break
        except Exception as e:
            logger.error("Profile %d failed: %s", profile.profile_id, e)
            continue

    logger.info("Scheduler — all profiles complete")


async def run_scheduled_cycle(service_factory: callable = None) -> None:
    """Run one scheduled cycle: refresh config + profiles from the DB, then run all.

    Settings and profiles are re-read from the store on **every** fire (ADR-031), so a
    cron edit, a provider/model change, or profile CRUD from the web Settings screen
    takes effect on the next trigger without a restart. The env bridge (ADR-035) pushes
    the current DB settings into ``os.environ`` so the evaluator, enrichment, and cost
    factories read the live configuration unchanged.

    Args:
        service_factory: Callable that builds a JobSearchService per profile. Defaults
            to ``service_factory.build_service`` (imported lazily to avoid a cycle).
    """
    from src.service_factory import build_service, build_settings_service

    settings_service = build_settings_service()
    settings_service.apply_to_environment()
    profiles = settings_service.list_profiles()
    if not profiles:
        logger.warning("Scheduled cycle skipped — no search profiles configured")
        return
    await run_all_profiles(profiles, service_factory or build_service)


def start_scheduler(
    profiles: list[SearchProfile],
    service_factory: callable,
    cron_expression: str,
    timezone: str,
) -> None:
    """Start a standalone ``BlockingScheduler`` for the CLI scheduled mode.

    This is the ``python -m src.main`` (no web server) path. The web deployment uses
    the in-process :class:`SchedulerManager` on FastAPI's lifespan instead (ADR-032);
    only that path can be rescheduled live. Runs indefinitely until the process stops.

    Args:
        profiles: Search profiles (used only for the startup log; each trigger reloads
            profiles from the DB via :func:`run_scheduled_cycle`).
        service_factory: Callable that builds a JobSearchService per profile.
        cron_expression: Standard cron expression (e.g. "0 8 * * 1-5").
        timezone: IANA timezone name (e.g. "America/New_York").
    """
    tz = pytz.timezone(timezone)
    scheduler = BlockingScheduler(timezone=tz)

    def job() -> None:
        """Execute one cycle synchronously inside the scheduler trigger."""
        asyncio.run(run_scheduled_cycle(service_factory))

    scheduler.add_job(
        job,
        CronTrigger.from_crontab(cron_expression, timezone=tz),
    )

    logger.info(
        "Scheduler started — cron: %s | timezone: %s",
        cron_expression,
        timezone,
    )
    logger.info("Running %d profile(s) per schedule", len(profiles))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


class SchedulerManager:
    """The in-process ``BackgroundScheduler`` the web server owns and reschedules live.

    ADR-032: uvicorn runs in the foreground and the scheduler runs in the **same
    process** as a ``BackgroundScheduler`` (not the standalone ``BlockingScheduler``),
    so a cron edit in the Settings screen reschedules the run job by a direct method
    call — no cross-process signalling, DB polling, or container restart.
    """

    _JOB_ID = "scheduled-run"

    def __init__(self) -> None:
        """Create an unstarted manager; call :meth:`start` to register the job."""
        self._scheduler: BackgroundScheduler | None = None

    @property
    def running(self) -> bool:
        """Whether the scheduler is started and holds the run job."""
        return self._scheduler is not None and self._scheduler.running

    def start(self, cron: str, timezone: str) -> None:
        """Start the scheduler and register the run job on the given cron/timezone.

        Args:
            cron: A 5-field crontab expression.
            timezone: IANA timezone name.
        """
        tz = pytz.timezone(timezone)
        self._scheduler = BackgroundScheduler(timezone=tz)
        self._scheduler.add_job(
            self._run,
            CronTrigger.from_crontab(cron, timezone=tz),
            id=self._JOB_ID,
        )
        self._scheduler.start()
        logger.info("In-process scheduler started — cron: %s | timezone: %s", cron, timezone)

    def reschedule(self, cron: str, timezone: str) -> None:
        """Re-point the run job at a new cron/timezone — the live-edit path.

        A no-op when the scheduler is not running.

        Args:
            cron: The new 5-field crontab expression.
            timezone: The new IANA timezone name.

        Raises:
            ValueError: When the cron expression or timezone is invalid.
        """
        if self._scheduler is None or not self._scheduler.running:
            return
        tz = pytz.timezone(timezone)
        self._scheduler.reschedule_job(
            self._JOB_ID, trigger=CronTrigger.from_crontab(cron, timezone=tz)
        )
        logger.info("Scheduler rescheduled — cron: %s | timezone: %s", cron, timezone)

    def shutdown(self) -> None:
        """Stop the scheduler (on app/process shutdown). Idempotent."""
        if self._scheduler is not None and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("In-process scheduler stopped")
        self._scheduler = None

    @staticmethod
    def _run() -> None:
        """Trigger entry point — run one cycle in a fresh event loop."""
        asyncio.run(run_scheduled_cycle())


_MANAGER: "SchedulerManager | None" = None


def get_scheduler_manager() -> "SchedulerManager | None":
    """Return the process-wide scheduler manager, or None when none is running."""
    return _MANAGER


def set_scheduler_manager(manager: "SchedulerManager | None") -> None:
    """Set or clear the process-wide scheduler manager (owned by the API lifespan)."""
    global _MANAGER
    _MANAGER = manager
