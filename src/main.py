"""CLI entrypoint for the Job Hunter AI Agent.

Loads environment variables, configures logging, resolves search profiles,
applies CLI overrides, and dispatches to either immediate run or scheduled mode.

Usage (immediate mode):
    python -m src.main
    python -m src.main --query "Senior Python Developer" --work-type remote

Usage (scheduled mode):
    Set SCHEDULE_ENABLED=true in .env then:
    python -m src.main
    docker-compose up -d
"""

import asyncio
import os

from dotenv import load_dotenv

from src.infra.logging import configure_logging
from src.cli.args import parse_args
from src.cli.overrides import apply_cli_overrides
from src.bootstrap import load_profiles
from src.runner import run_immediate
from src.scheduler import start_scheduler
from src.service_factory import build_service


async def main() -> None:
    """Wire adapters, load profiles, and dispatch to immediate or scheduled mode."""
    load_dotenv()
    configure_logging()

    args = parse_args()
    profiles = load_profiles()
    apply_cli_overrides(profiles, args)

    if os.getenv("SCHEDULE_ENABLED", "false").lower() == "true":
        start_scheduler(
            profiles=profiles,
            service_factory=build_service,
            cron_expression=os.getenv("SCHEDULE_CRON", "0 8 * * 1-5"),
            timezone=os.getenv("SCHEDULE_TIMEZONE", "America/New_York"),
        )
    else:
        await run_immediate(
            profiles=profiles,
            service_factory=build_service,
        )


if __name__ == "__main__":
    asyncio.run(main())
