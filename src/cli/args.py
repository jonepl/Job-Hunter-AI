"""CLI argument definitions for the Job Hunter AI Agent.

The default (no-subcommand) invocation runs a search and takes all --query,
--location, --work-type, --date-posted, and --scrapers arguments; all are
optional and fall back to .env configuration via SearchProfile. The ``mark``
subcommand moves a stored job through its lifecycle (ADR-025).
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


def parse_args() -> argparse.Namespace:
    """Parse and return CLI arguments.

    With no subcommand the app runs a search; all search arguments are optional
    and fall back to .env values via SearchProfile.load_all(). The ``mark``
    subcommand marks a stored job (``args.command == "mark"``).

    Returns:
        Namespace whose ``command`` is None (search) or "mark". Search runs carry
        query/location/work_type/date_posted/scrapers/evaluator_model; mark runs
        carry job_id/status/note/save/unsave.
    """
    parser = argparse.ArgumentParser(
        description="Job Hunter AI Agent — scrapes, evaluates, and ranks job listings."
    )
    subparsers = parser.add_subparsers(dest="command")
    _add_mark_subparser(subparsers)
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
