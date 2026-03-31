"""Entry point for the Job Hunter AI Agent.

Loads environment variables, resolves search profiles, and runs all profiles
either immediately or on a cron schedule depending on SCHEDULE_ENABLED in .env.

Usage (immediate mode):
    python -m src.main
    python -m src.main --query "Senior Python Developer" --work-type remote
    python -m src.main --query "Senior Python Developer" --location "New York" --work-type hybrid

Usage (scheduled mode):
    Set SCHEDULE_ENABLED=true in .env, then:
    python -m src.main
    docker-compose up -d
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.domain.work_type import WorkType
from src.scheduler import start_scheduler
from src.service_factory import build_service

_logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure console and file logging for the agent run.

    Writes INFO+ to stdout and to logs/agent_<timestamp>.log.
    Creates the logs/ directory if it does not exist.
    """
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join("logs", f"agent_{timestamp}.log")

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[stream_handler, file_handler],
    )


def _parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    All arguments are optional — values can come from .env via SearchProfile.
    CLI args override .env values for all profiles when provided.

    Returns:
        Namespace with optional query, location, work_type, date_posted,
        and scrapers attributes.
    """
    parser = argparse.ArgumentParser(
        description="Job Hunter AI Agent — scrapes, evaluates, and ranks job listings."
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help=(
            "Job search query. Overrides SEARCH_QUERY or PROFILE_N_QUERY "
            "in .env for all profiles."
        ),
    )
    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help=(
            "Job search location. Overrides SEARCH_LOCATION or "
            "PROFILE_N_LOCATION in .env."
        ),
    )
    parser.add_argument(
        "--work-type",
        type=str,
        nargs="+",
        choices=["remote", "hybrid", "onsite"],
        default=None,
        dest="work_type",
        help="Job work type filter. One or more of: remote, hybrid, onsite.",
    )
    parser.add_argument(
        "--date-posted",
        type=str,
        default=None,
        dest="date_posted",
        help=(
            "Filter jobs by posting recency. "
            "Overrides DATE_POSTED in .env. "
            "Supported: 24h, 3days, week, month."
        ),
    )
    parser.add_argument(
        "--scrapers",
        type=str,
        default=None,
        help=(
            "Comma-separated list of scrapers to use. "
            "Overrides ACTIVE_SCRAPERS or PROFILE_N_SCRAPERS in .env. "
            "Supported: linkedin, indeed, glassdoor, ziprecruiter."
        ),
    )
    return parser.parse_args()


def _require_env(key: str) -> str:
    """Return the value of a required environment variable.

    Args:
        key: The environment variable name.

    Returns:
        The variable value.

    Raises:
        SystemExit: If the variable is not set.
    """
    value = os.getenv(key)
    if not value:
        logging.critical("Required environment variable %s is not set. Check your .env file.", key)
        sys.exit(1)
    return value


async def main() -> None:
    """Wire adapters, load profiles, and run the pipeline in immediate or scheduled mode."""
    load_dotenv()
    _configure_logging()

    logger = logging.getLogger(__name__)
    args = _parse_args()

    # Load all profiles from .env
    try:
        profiles = SearchProfile.load_all()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Apply CLI overrides to all profiles when args are provided
    if args.query:
        for p in profiles:
            p.query = args.query

    if args.location:
        for p in profiles:
            p.location = args.location

    if args.work_type:
        work_types = [WorkType(w.lower()) for w in args.work_type]
        for p in profiles:
            p.work_types = work_types

    if args.date_posted:
        try:
            date_posted = DatePosted.from_string(args.date_posted)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        for p in profiles:
            p.date_posted = date_posted

    if args.scrapers:
        try:
            scrapers = ScraperName.parse_list(args.scrapers)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        for p in profiles:
            p.active_scrapers = scrapers

    # Check SCHEDULE_ENABLED
    schedule_enabled = os.getenv("SCHEDULE_ENABLED", "false").lower() == "true"

    if schedule_enabled:
        cron = os.getenv("SCHEDULE_CRON", "0 8 * * 1-5")
        timezone = os.getenv("SCHEDULE_TIMEZONE", "America/New_York")
        logger.info("Scheduler mode enabled")
        logger.info("Cron       : %s", cron)
        logger.info("Timezone   : %s", timezone)
        logger.info("Profiles   : %d", len(profiles))
        start_scheduler(
            profiles=profiles,
            service_factory=build_service,
            cron_expression=cron,
            timezone=timezone,
        )
    else:
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
                service = build_service(profile)
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
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
