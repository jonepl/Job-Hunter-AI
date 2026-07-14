"""Scheduler — APScheduler-based in-process job scheduler for multi-profile runs."""

import asyncio
import logging
import os

import pytz
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
