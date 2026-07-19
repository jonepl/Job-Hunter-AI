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
import sys

from dotenv import load_dotenv

from src.infra.logging import configure_logging
from src.cli.args import parse_args
from src.cli.overrides import apply_cli_overrides, apply_evaluator_override
from src.bootstrap import load_profiles
from src.runner import run_immediate
from src.scheduler import start_scheduler
from src.service_factory import build_service


async def main() -> None:
    """Wire adapters, load profiles, and dispatch to mark, immediate, or scheduled mode."""
    load_dotenv()
    configure_logging()

    args = parse_args()

    if args.command == "mark":
        _dispatch_mark(args)
        return

    if args.command == "resume":
        _dispatch_resume(args)
        return

    if args.command == "generate":
        await _dispatch_generate(args)
        return

    profiles = load_profiles()

    # Apply DB-backed settings into the environment (W7 env bridge, ADR-035) so the
    # evaluator/enrichment/schedule factories read the current config. Runs before the
    # CLI overrides so precedence stays .env → DB → CLI (CLI wins, for testing).
    from src.service_factory import build_settings_service

    build_settings_service().apply_to_environment()

    apply_cli_overrides(profiles, args)
    apply_evaluator_override(args)

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


def _dispatch_mark(args) -> None:
    """Run the ``mark`` subcommand: mutate one stored job, print, and exit.

    Args:
        args: The parsed ``mark`` namespace (job_id, status, note, save, unsave).
    """
    from src.adapters.repository.factory import build_repository
    from src.core.domain.job_status import JobStatus
    from src.mark_runner import run_mark

    status = JobStatus(args.status) if args.status else None
    saved = True if args.save else (False if args.unsave else None)

    message, exit_code = run_mark(
        repository=build_repository(),
        job_id=args.job_id,
        status=status,
        note=args.note,
        saved=saved,
    )
    print(message)
    sys.exit(exit_code)


def _dispatch_resume(args) -> None:
    """Run the ``resume`` subcommand: manage the cached master resume, then exit.

    Args:
        args: The parsed ``resume`` namespace (resume_action plus its arguments).
    """
    from src.resume_runner import (
        run_resume_activate,
        run_resume_list,
        run_resume_upload,
    )
    from src.service_factory import build_resume_service

    action = getattr(args, "resume_action", None)
    if action is None:
        print("Specify a resume action: upload <path> | list | activate <version>")
        sys.exit(2)

    service = build_resume_service()
    if action == "upload":
        message, exit_code = run_resume_upload(service, args.path)
    elif action == "list":
        message, exit_code = run_resume_list(service)
    else:  # activate
        message, exit_code = run_resume_activate(service, args.version)

    print(message)
    sys.exit(exit_code)


async def _dispatch_generate(args) -> None:
    """Run the ``generate`` subcommand: produce a document, print, and exit.

    Args:
        args: The parsed ``generate`` namespace (generate_kind, job_id, and, for
            cover letters, the optional voice overrides).
    """
    from src.core.domain.voice_descriptor import VoiceDescriptor
    from src.generation_runner import (
        run_generate_cover_letter,
        run_generate_resume,
    )
    from src.service_factory import build_generation_service

    kind = getattr(args, "generate_kind", None)
    if kind is None:
        print("Specify what to generate: resume <job_id> | cover-letter <job_id>")
        sys.exit(2)

    service = build_generation_service()
    if kind == "resume":
        message, exit_code = await run_generate_resume(service, args.job_id)
    else:  # cover-letter
        voice = VoiceDescriptor(
            tone=(args.tone or os.getenv("VOICE_TONE", "direct")),
            person=(args.person or os.getenv("VOICE_PERSON", "first_person")),
            style_notes=(
                args.style_notes
                if args.style_notes is not None
                else os.getenv("VOICE_STYLE_NOTES", "")
            ),
        )
        message, exit_code = await run_generate_cover_letter(
            service, args.job_id, voice
        )

    print(message)
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
