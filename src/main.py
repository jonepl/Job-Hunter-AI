"""CLI entrypoint for the Job Hunter AI Agent.

Loads environment variables, configures logging, resolves search profiles,
applies CLI overrides, and runs an immediate, in-process pipeline run. The CLI has
no scheduled mode — scheduling is owned solely by the web server (ADR-032).

Usage (immediate mode):
    python -m src.main
    python -m src.main --query "Senior Python Developer" --work-type remote
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from src.cli.args import parse_args
from src.cli.overrides import apply_cli_overrides, apply_evaluator_override
from src.infra.logging import configure_logging
from src.orchestration.bootstrap import load_profiles
from src.orchestration.runner import run_immediate
from src.orchestration.service_factory import build_service

logger = logging.getLogger(__name__)


async def main() -> None:
    """Wire adapters, load profiles, apply overrides, and run an immediate pipeline run."""
    load_dotenv()
    configure_logging()

    args = parse_args()

    profiles = load_profiles()

    # Apply DB-backed settings into the environment (W7 env bridge, ADR-035) so the
    # evaluator/enrichment/schedule factories read the current config. Runs before the
    # CLI overrides so precedence stays .env → DB → CLI (CLI wins, for testing).
    from src.orchestration.service_factory import build_settings_service

    settings_service = build_settings_service()
    settings_service.apply_to_environment()

    apply_cli_overrides(profiles, args)
    apply_evaluator_override(args)

    # The CLI has no scheduled mode — it always runs all profiles once and exits.
    # Scheduling is owned solely by the web server's SchedulerManager (ADR-032). Flag
    # a SCHEDULE_ENABLED=true .env that an operator may expect the CLI to honor.
    if os.getenv("SCHEDULE_ENABLED", "false").lower() == "true":
        logger.warning(
            "SCHEDULE_ENABLED is honored only by the web server; CLI runs once and exits."
        )

    await run_immediate(
        profiles=profiles,
        service_factory=build_service,
        settings_service=settings_service,
    )


if __name__ == "__main__":
    asyncio.run(main())
