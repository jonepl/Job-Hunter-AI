"""Scheduler — APScheduler-based in-process job scheduler for multi-profile runs."""

import asyncio
import logging

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.domain.search_profile import SearchProfile

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
    for profile in profiles:
        logger.info(
            "Running profile %d: %s | %s",
            profile.profile_id,
            profile.query,
            profile.location,
        )
        try:
            service = service_factory(profile)
            await service.run(
                query=profile.query,
                location=profile.location,
                threshold=profile.score_threshold,
                top_results=profile.top_results,
                work_types=profile.work_types,
                date_posted=profile.date_posted,
            )
        except Exception as e:
            logger.error("Profile %d failed: %s", profile.profile_id, e)
            continue

    logger.info("Scheduler — all profiles complete")


def start_scheduler(
    profiles: list[SearchProfile],
    service_factory: callable,
    cron_expression: str,
    timezone: str,
) -> None:
    """Start APScheduler with the given cron expression.

    Runs indefinitely until the container stops.

    Args:
        profiles: List of SearchProfile instances to run on each trigger.
        service_factory: Callable that builds a JobSearchService per profile.
        cron_expression: Standard cron expression (e.g. "0 8 * * 1-5").
        timezone: IANA timezone name (e.g. "America/New_York").
    """
    tz = pytz.timezone(timezone)
    scheduler = BlockingScheduler(timezone=tz)

    def job() -> None:
        """Execute all profiles synchronously inside the scheduler trigger."""
        asyncio.run(run_all_profiles(profiles, service_factory))

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
