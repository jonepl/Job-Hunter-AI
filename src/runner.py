"""Immediate run execution for the Job Hunter AI Agent.

Runs all search profiles sequentially in immediate mode — one run per profile,
then exits. Used by both the CLI entrypoint and future API entrypoint.

Contains no CLI or argparse dependency. Accepts plain Python objects only.
"""

import logging
import sys
from typing import Callable

from src.core.domain.run_report import RunReport
from src.core.domain.search_profile import SearchProfile
from src.core.services.job_search_service import JobSearchService

logger = logging.getLogger(__name__)


async def run_immediate(
    profiles: list[SearchProfile],
    service_factory: Callable[[SearchProfile], JobSearchService],
) -> None:
    """Run all profiles immediately and exit.

    Iterates all profiles sequentially. Builds a fresh service instance per
    profile. Logs results after each run. Exits with code 1 on unrecoverable
    errors.

    Args:
        profiles: List of SearchProfile instances to run.
        service_factory: Callable that accepts a SearchProfile and returns a
            configured JobSearchService.
    """
    logger.info("Immediate run mode")
    logger.info("Profiles : %d", len(profiles))

    for profile in profiles:
        logger.info(
            "Profile %d: %s | %s",
            profile.profile_id,
            profile.query,
            profile.location,
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
            )
            logger.info("=" * 60)
            _log_report_results(profile, report, logger)
            logger.info("=" * 60)

        except FileNotFoundError as exc:
            logger.critical("Resume file not found: %s", exc)
            logger.critical("Mount your resume PDF to docs/resume/resume.pdf and try again.")
            sys.exit(1)
        except Exception as exc:
            logger.critical(
                "Unexpected error during profile %d pipeline: %s",
                profile.profile_id,
                exc,
                exc_info=True,
            )
            continue


def _log_report_results(
    profile: SearchProfile,
    report: RunReport,
    logger: logging.Logger,
) -> None:
    """Log RunReport results for a completed profile run.

    Logs qualifying results with rank, score, title, company, platform,
    and hire recommendation. Logs near-miss warning with suggested threshold
    when zero qualifying results.

    Args:
        profile: The SearchProfile that was run.
        report: The RunReport returned by the pipeline.
        logger: Logger instance to use.
    """
    if report.has_qualifying_results:
        logger.info(
            "Profile %d complete — %d result(s) returned",
            profile.profile_id,
            len(report.qualifying_results),
        )
        for i, result in enumerate(report.qualifying_results, start=1):
            logger.info(
                "  %d. [%d] %s @ %s (%s) — %s",
                i,
                result.score,
                result.job.title,
                result.job.company,
                result.job.platform,
                result.hire_recommendation,
            )
    else:
        logger.warning(
            "Profile %d complete — 0 qualifying results above threshold %d",
            profile.profile_id,
            profile.score_threshold,
        )
        if report.near_miss_results:
            top = report.near_miss_results[0]
            logger.warning(
                "Top near-miss: [%d] %s @ %s",
                top.score,
                top.job.title,
                top.job.company,
            )
            logger.warning(
                "Consider lowering SCORE_THRESHOLD to %d in your .env file",
                report.suggested_threshold,
            )
