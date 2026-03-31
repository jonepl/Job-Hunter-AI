"""ServiceFactory — builds a fully wired JobSearchService for a given SearchProfile."""

import os

from src.adapters.evaluator.factory import build_evaluator
from src.adapters.output.email_output import EmailOutput
from src.adapters.output.file_output import FileOutput
from src.adapters.scrapers.scraper_factory import build_scrapers
from src.core.domain.search_profile import SearchProfile
from src.core.services.job_search_service import JobSearchService


def build_service(profile: SearchProfile) -> JobSearchService:
    """Build a fully wired JobSearchService for the given SearchProfile.

    Instantiates scrapers, evaluator, and output adapters from the profile
    and environment variables.

    Args:
        profile: The SearchProfile defining which scrapers and settings to use.

    Returns:
        A configured JobSearchService ready to run.
    """
    # Build scrapers from profile
    scrapers = build_scrapers(profile.active_scrapers)

    # Build evaluator from .env provider
    evaluator = build_evaluator()

    # Build output adapters
    gmail_address = os.getenv("GMAIL_ADDRESS", "")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "")
    email_recipient = os.getenv("EMAIL_RECIPIENT", "")

    outputs = [
        EmailOutput(
            sender=gmail_address,
            password=gmail_app_password,
            recipient=email_recipient,
        ),
        FileOutput(output_dir="output"),
    ]

    return JobSearchService(
        scrapers=scrapers,
        evaluator=evaluator,
        outputs=outputs,
    )
