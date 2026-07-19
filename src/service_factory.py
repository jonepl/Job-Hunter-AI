"""ServiceFactory — builds a fully wired JobSearchService for a given SearchProfile."""

import os

from src.adapters.enrichment.factory import build_enrichment
from src.adapters.evaluator.factory import build_evaluator
from src.adapters.output.email_output import EmailOutput
from src.adapters.output.file_output import FileOutput
from src.adapters.repository.factory import build_repository, build_resume_repository
from src.adapters.resume.factory import build_resume_parser
from src.adapters.scrapers.scraper_factory import build_scrapers
from src.core.domain.search_profile import SearchProfile
from src.core.services.job_search_service import JobSearchService
from src.core.services.resume_service import ResumeService


def build_resume_service() -> ResumeService:
    """Build the ResumeService from the parser and resume repository (ADR-028).

    Shared by the pipeline (auto-seed + cache read) and the ``resume`` CLI so
    parsing, hashing, and the size guard live in exactly one place.

    Returns:
        A ready ResumeService.
    """
    return ResumeService(build_resume_parser(), build_resume_repository())


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

    # Build the optional pre-filter (None when ENRICHMENT_ENABLED is not true)
    enrichment = build_enrichment()
    enrichment_mode = os.getenv("ENRICHMENT_MODE", "shadow").strip().lower()
    if enrichment_mode not in ("shadow", "enforce"):
        enrichment_mode = "shadow"

    # Build the persistence repository (shared singleton across profiles)
    repository = build_repository()

    # Build the master-resume service — the pipeline reads the cached resume and
    # auto-seeds it on a first run rather than re-parsing the PDF every run (ADR-028).
    resume_service = build_resume_service()

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
        resume_path=os.getenv("RESUME_PATH", "docs/resume/resume.pdf"),
        enrichment=enrichment,
        enrichment_mode=enrichment_mode,
        repository=repository,
        resume_service=resume_service,
    )
