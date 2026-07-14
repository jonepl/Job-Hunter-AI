"""CLI argument definitions for the Job Hunter AI Agent.

Defines all --query, --location, --work-type, --date-posted, and --scrapers
arguments. All arguments are optional — values fall back to .env configuration
via SearchProfile.
"""

import argparse


def parse_args() -> argparse.Namespace:
    """Parse and return CLI arguments.

    All arguments are optional. When not provided the app falls back to .env
    values via SearchProfile.load_all().

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
