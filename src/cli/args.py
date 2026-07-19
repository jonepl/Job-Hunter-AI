"""CLI argument definitions for the Job Hunter AI Agent.

The default (no-subcommand) invocation runs a search and takes all --query,
--location, --work-type, --date-posted, and --scrapers arguments; all are
optional and fall back to .env configuration via SearchProfile. The ``mark``
subcommand moves a stored job through its lifecycle (ADR-025); the ``resume``
subcommand manages the cached master resume (ADR-028); the ``generate`` subcommand
produces a tailored resume or cover letter for a stored job (F, ADR-029).
"""

import argparse

# The six human-set statuses — the only ones a person may assign via ``mark``.
# Machine states (new / evaluated / pre_filtered) are never user-selectable.
_MARK_STATUS_CHOICES = [
    "applied",
    "started",
    "interviewing",
    "offer",
    "rejected",
    "not_interested",
]

_VOICE_TONE_CHOICES = ["direct", "warm", "formal", "bold"]
_VOICE_PERSON_CHOICES = ["first_person", "implied"]


def parse_args() -> argparse.Namespace:
    """Parse and return CLI arguments.

    With no subcommand the app runs a search; all search arguments are optional
    and fall back to .env values via SearchProfile.load_all(). The ``mark``
    subcommand marks a stored job (``args.command == "mark"``).

    Returns:
        Namespace whose ``command`` is None (search), "mark", "resume", or
        "generate". Search runs carry query/location/work_type/date_posted/
        scrapers/evaluator_model; mark runs carry job_id/status/note/save/unsave;
        resume runs carry a ``resume_action`` (upload/list/activate); generate runs
        carry a ``generate_kind`` (resume/cover-letter), a job id, and voice flags.
    """
    parser = argparse.ArgumentParser(
        description="Job Hunter AI Agent — scrapes, evaluates, and ranks job listings."
    )
    subparsers = parser.add_subparsers(dest="command")
    _add_mark_subparser(subparsers)
    _add_resume_subparser(subparsers)
    _add_generate_subparser(subparsers)
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
    parser.add_argument(
        "--evaluator-model",
        type=str,
        default=None,
        dest="evaluator_model",
        help=(
            "LLM model name for the evaluator. Overrides EVALUATOR_MODEL in "
            ".env for this run. Must be valid for the active EVALUATOR_PROVIDER "
            "(e.g. gpt-4o for openai, claude-sonnet-4-5 for anthropic)."
        ),
    )
    return parser.parse_args()


def _add_mark_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``mark`` subcommand for lifecycle mutations (ADR-025).

    Args:
        subparsers: The subparsers action to attach the ``mark`` parser to.
    """
    mark = subparsers.add_parser(
        "mark",
        help="Mark a stored job's status and/or save state.",
        description=(
            "Move a stored job through its lifecycle. Find job ids via "
            "GET /api/jobs or sqlite3. At least one of --status/--save/--unsave "
            "is required."
        ),
    )
    mark.add_argument(
        "--job-id",
        type=int,
        required=True,
        dest="job_id",
        help="The repository id of the job to mark.",
    )
    mark.add_argument(
        "--status",
        type=str,
        default=None,
        choices=_MARK_STATUS_CHOICES,
        help="New human-set status. One of: " + ", ".join(_MARK_STATUS_CHOICES) + ".",
    )
    mark.add_argument(
        "--note",
        type=str,
        default=None,
        help="Optional note recorded on the status-history row.",
    )
    save_group = mark.add_mutually_exclusive_group()
    save_group.add_argument(
        "--save",
        action="store_true",
        help="Bookmark the job (independent of status).",
    )
    save_group.add_argument(
        "--unsave",
        action="store_true",
        help="Remove the job's bookmark.",
    )


def _add_resume_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``resume`` subcommand for master-resume management (ADR-028).

    ``resume upload <path>`` parses and caches a resume as a new active version;
    ``resume list`` shows stored versions; ``resume activate <version>`` restores
    an earlier version. The pipeline reads the active version instead of
    re-parsing the PDF every run.

    Args:
        subparsers: The subparsers action to attach the ``resume`` parser to.
    """
    resume = subparsers.add_parser(
        "resume",
        help="Manage the cached master resume (upload / list / activate).",
        description=(
            "Parse the master resume once and cache it so runs stop re-parsing "
            "the PDF (ADR-028). Keeps a version history with restore."
        ),
    )
    actions = resume.add_subparsers(dest="resume_action")

    upload = actions.add_parser(
        "upload",
        help="Parse a resume file and store it as the active version.",
    )
    upload.add_argument(
        "path",
        type=str,
        help="Path to the resume PDF to parse and cache.",
    )

    actions.add_parser(
        "list",
        help="List stored resume versions (the active one is marked).",
    )

    activate = actions.add_parser(
        "activate",
        help="Restore an earlier stored version by number.",
    )
    activate.add_argument(
        "version",
        type=int,
        help="The version number to activate.",
    )


def _add_generate_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``generate`` subcommand for document generation (F, ADR-029).

    ``generate resume <job_id>`` produces a tailored resume ``.docx``;
    ``generate cover-letter <job_id>`` produces a cover letter in the candidate's
    voice (``--tone`` / ``--person`` / ``--style-notes`` override the ``.env``
    seeds). Only the file path and provenance are ever printed, never content.

    Args:
        subparsers: The subparsers action to attach the ``generate`` parser to.
    """
    generate = subparsers.add_parser(
        "generate",
        help="Generate a tailored resume or cover letter for a stored job.",
        description=(
            "Turn a stored, evaluated job into a tailored resume or cover-letter "
            ".docx. The document is written to disk; only its path and provenance "
            "are printed (F, ADR-029)."
        ),
    )
    kinds = generate.add_subparsers(dest="generate_kind")

    resume_gen = kinds.add_parser(
        "resume",
        help="Generate a resume tailored to a stored job.",
    )
    resume_gen.add_argument(
        "job_id",
        type=int,
        help="The repository id of the job to tailor to.",
    )

    letter = kinds.add_parser(
        "cover-letter",
        help="Generate a cover letter for a stored job in your voice.",
    )
    letter.add_argument(
        "job_id",
        type=int,
        help="The repository id of the job to write a letter for.",
    )
    letter.add_argument(
        "--tone",
        type=str,
        default=None,
        choices=_VOICE_TONE_CHOICES,
        help="Voice tone preset. Overrides VOICE_TONE in .env.",
    )
    letter.add_argument(
        "--person",
        type=str,
        default=None,
        choices=_VOICE_PERSON_CHOICES,
        help="Point of view. Overrides VOICE_PERSON in .env.",
    )
    letter.add_argument(
        "--style-notes",
        type=str,
        default=None,
        dest="style_notes",
        help="Free-text style instructions. Overrides VOICE_STYLE_NOTES in .env.",
    )
