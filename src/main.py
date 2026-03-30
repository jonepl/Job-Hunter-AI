"""Entry point for the Job Hunter AI Agent.

Loads environment variables, wires all adapters into JobSearchService,
and executes the full pipeline from the command line.

Usage:
    python -m src.main --query "Senior Python Developer" --work-type remote
    python -m src.main --query "Senior Python Developer" --location "New York" --work-type hybrid
    python -m src.main --query "Senior Python Developer" --location "Remote"
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from src.adapters.evaluator.factory import build_evaluator
from src.adapters.output.email_output import EmailOutput
from src.adapters.output.file_output import FileOutput
from src.adapters.scrapers.jsearch import JSearchScraper
from src.adapters.scrapers.linkedin import LinkedInScraper
from src.core.domain.work_type import WorkType
from src.core.services.job_search_service import JobSearchService

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

    Returns:
        Namespace with query, location, and work_type attributes.
    """
    parser = argparse.ArgumentParser(
        description="Job Hunter AI Agent — scrapes, evaluates, and ranks job listings."
    )
    parser.add_argument(
        "--query",
        required=True,
        help='Job search query (e.g. "Senior Python Developer")',
    )
    parser.add_argument(
        "--location",
        type=str,
        required=False,
        default=None,
        help=(
            "Job search location. "
            "Required for --work-type hybrid and --work-type onsite. "
            "Optional for --work-type remote — defaults to 'United States' when not provided. "
            "Example: --location 'New York'"
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
    return parser.parse_args()


def _resolve_location(args: argparse.Namespace) -> tuple[str, bool, set[WorkType] | None]:
    """Resolve the effective location from parsed CLI arguments.

    Applies the following rules:
    - --work-type remote only, no --location → defaults to "United States"
    - --work-type remote only, --location provided → use as-is
    - --work-type hybrid/onsite or mixed, no --location → error + exit
    - No --work-type, no --location → error + exit
    - No --work-type, --location provided → use as-is

    Args:
        args: Parsed argparse namespace containing location and work_type.

    Returns:
        Tuple of (resolved_location, was_defaulted) where was_defaulted is True
        when the location was automatically set to "United States".
    """
    location = args.location
    work_types = (
        {WorkType(wt) for wt in args.work_type}
        if args.work_type is not None
        else None
    )

    if work_types is not None:
        if WorkType.REMOTE in work_types and len(work_types) == 1:
            if location is None:
                location = "United States"
                _logger.info(
                    "Location not provided — defaulting to 'United States' for remote work type"
                )
                return location, True, work_types
        else:
            if location is None:
                print(
                    "Error: --location is required for --work-type hybrid and --work-type onsite.\n"
                    "Example: --location 'New York'"
                )
                sys.exit(1)
    else:
        if location is None:
            print(
                "Error: --location is required when --work-type is not specified.\n"
                "Example: --location 'Remote' or --location 'United States'"
            )
            sys.exit(1)

    return location, False, work_types


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
    """Wire adapters, build the service, and run the full pipeline."""
    load_dotenv()
    _configure_logging()

    logger = logging.getLogger(__name__)
    args = _parse_args()
    location, location_defaulted, work_types = _resolve_location(args)

    logger.info("=" * 60)
    logger.info("Job Search Agent — starting run")
    logger.info("Query    : %s", args.query)
    logger.info("Location : %s", location)
    if location_defaulted:
        logger.info("           (defaulted from --work-type remote)")
    logger.info("=" * 60)

    # Load required environment variables
    gmail_address = _require_env("GMAIL_ADDRESS")
    gmail_app_password = _require_env("GMAIL_APP_PASSWORD")
    email_recipient = _require_env("EMAIL_RECIPIENT")
    score_threshold = int(os.getenv("SCORE_THRESHOLD", "70"))

    # Load optional TOP_RESULTS
    top_results_env = os.getenv("TOP_RESULTS")
    top_results = int(top_results_env) if top_results_env else None

    logger.info("Score threshold : %d", score_threshold)
    if top_results is not None:
        logger.info("Top results cap : %d", top_results)
    else:
        logger.info("Top results cap : not set (all qualifying results returned)")

    # Instantiate scraper adapters
    scrapers = [
        # LinkedInScraper(),
        JSearchScraper(platform="indeed"),
        # JSearchScraper(platform="glassdoor"),
        # JSearchScraper(platform="ziprecruiter"),
    ]
    logger.info("Scrapers registered: LinkedIn, Indeed, Glassdoor, ZipRecruiter")

    # Instantiate evaluator adapter
    evaluator = build_evaluator()

    # Instantiate output adapters
    outputs = [
        EmailOutput(
            sender=gmail_address,
            password=gmail_app_password,
            recipient=email_recipient,
        ),
        FileOutput(output_dir="output"),
    ]
    logger.info("Outputs registered: EmailOutput, FileOutput")

    # Wire into JobSearchService
    service = JobSearchService(
        scrapers=scrapers,
        evaluator=evaluator,
        outputs=outputs,
        resume_path="docs/resume/resume.pdf",
    )

    try:
        report = await service.run(
            query=args.query,
            location=location,
            threshold=score_threshold,
            top_results=top_results,
            work_types=work_types,
        )

        logger.info("=" * 60)
        if report.has_qualifying_results:
            logger.info(
                "Run complete — %d result(s) returned",
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
            logger.warning("Run complete — 0 qualifying results above threshold %d", score_threshold)
            logger.warning(
                "Score threshold %d was not met by any evaluated job", score_threshold
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
        logger.critical("Unexpected error during pipeline: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
