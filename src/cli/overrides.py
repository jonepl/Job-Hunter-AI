"""CLI override application for search profiles.

Applies parsed CLI arguments to all loaded SearchProfile instances.
CLI values always take precedence over .env values when provided.
"""

import argparse
import sys

from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.domain.work_type import WorkType


def apply_cli_overrides(
    profiles: list[SearchProfile],
    args: argparse.Namespace,
) -> None:
    """Apply CLI argument overrides to all search profiles.

    Modifies profiles in place. Only applies overrides for arguments
    that were explicitly provided — None values are ignored.

    Args:
        profiles: List of SearchProfile instances to modify.
        args: Parsed CLI arguments from parse_args().
    """
    if args.query:
        for p in profiles:
            p.query = args.query

    if args.location:
        for p in profiles:
            p.location = args.location

    if args.work_type:
        work_types = [
            WorkType(w.lower())
            for w in args.work_type
        ]
        for p in profiles:
            p.work_types = work_types

    if args.date_posted:
        try:
            date_posted = DatePosted.from_string(args.date_posted)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        for p in profiles:
            p.date_posted = date_posted

    if args.scrapers:
        try:
            scrapers = ScraperName.parse_list(args.scrapers)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        for p in profiles:
            p.active_scrapers = scrapers
