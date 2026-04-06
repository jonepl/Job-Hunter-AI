"""Immediate run execution for the Job Hunter AI Agent.

Runs all search profiles sequentially in immediate mode — one run per profile,
then exits. Used by both the CLI entrypoint and future API entrypoint.

Contains no CLI or argparse dependency. Accepts plain Python objects only.
"""

import logging
import os
import sys
from typing import Callable

from src.core.domain.run_report import RunReport
from src.core.domain.search_profile import SearchProfile
from src.core.services.job_search_service import JobSearchService
from src.infra.cost_estimator import estimate_run_cost
from src.infra.cost_tracker import CostTracker

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

    # Load cost tracking config once
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
            "Profile %d: %s | %s",
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
