"""ServiceFactory — builds a fully wired JobSearchService for a given SearchProfile."""

import os

from src.adapters.enrichment.factory import build_enrichment
from src.adapters.evaluator.factory import build_evaluator
from src.adapters.generation.factory import (
    build_cover_letter,
    build_docx_writer,
    build_resume_tailor,
)
from src.adapters.output.email_output import EmailOutput
from src.adapters.output.file_output import FileOutput
from src.adapters.repository.factory import (
    build_generation_repository,
    build_profile_repository,
    build_repository,
    build_resume_repository,
    build_run_repository,
    build_settings_repository,
)
from src.adapters.resume.factory import build_resume_parser
from src.adapters.scrapers.scraper_factory import build_scrapers
from src.core.domain.search_profile import SearchProfile
from src.core.services.generation_service import GenerationService
from src.core.services.job_search_service import JobSearchService
from src.core.services.resume_service import ResumeService
from src.core.services.run_service import RunService
from src.core.services.settings_service import SettingsService


def build_settings_service() -> SettingsService:
    """Build the SettingsService over the settings + profile repositories (W7).

    Shared by the run pipeline (seed + per-run env bridge) and the API's Settings
    routes so the DB-backed config lives in exactly one place (ADR-031).

    Returns:
        A ready SettingsService.
    """
    return SettingsService(build_settings_repository(), build_profile_repository())


def build_resume_service() -> ResumeService:
    """Build the ResumeService from the parser and resume repository (ADR-028).

    Shared by the pipeline (auto-seed + cache read) and the ``resume`` CLI so
    parsing, hashing, and the size guard live in exactly one place.

    Returns:
        A ready ResumeService.
    """
    return ResumeService(build_resume_parser(), build_resume_repository())


def build_generation_service() -> GenerationService:
    """Build the GenerationService for the ``generate`` CLI (and later W6) (F).

    Assembles the tailor + cover-letter adapters (behind the ``openai|anthropic``
    allowlist), the ``.docx`` writer, the generation repository, the resume service,
    and the job repository. Reads ``GENERATIONS_DIR`` for the output directory.

    Returns:
        A ready GenerationService.
    """
    return GenerationService(
        tailor=build_resume_tailor(),
        cover_letter=build_cover_letter(),
        writer=build_docx_writer(),
        generation_repo=build_generation_repository(),
        resume_service=build_resume_service(),
        job_repository=build_repository(),
        generations_dir=os.getenv("GENERATIONS_DIR", "data/generations"),
        generation_timeout_seconds=float(os.getenv("GENERATION_TIMEOUT_SECONDS", "120")),
    )


def build_run_service() -> RunService:
    """Build the RunService for the web "Run search now" flow (W8).

    Wires the run repository, the DB-backed settings service (env bridge + profile
    reload), the per-profile service factory, and the sequential multi-profile runner
    so a web run executes exactly what a scheduled fire does. Reads
    ``RUN_TIMEOUT_SECONDS`` for the lost-task timeout.

    Returns:
        A ready RunService.
    """
    # Imported here (not at module top) to avoid a scheduler ↔ service_factory
    # import cycle: the scheduler imports build_service from this module lazily.
    from src.orchestration.scheduler import run_all_profiles

    return RunService(
        run_repo=build_run_repository(),
        settings_service=build_settings_service(),
        service_factory=build_service,
        run_all_profiles=run_all_profiles,
        run_timeout_seconds=float(os.getenv("RUN_TIMEOUT_SECONDS", "1800")),
    )


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
