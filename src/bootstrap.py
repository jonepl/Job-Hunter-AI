"""Application bootstrap for the Job Hunter AI Agent.

Loads and validates search profiles from environment configuration.
Contains no CLI or API dependency — accepts plain Python objects so it
can be reused by both the CLI entrypoint and a future API entrypoint.
"""

import sys

from src.core.domain.search_profile import SearchProfile


def load_profiles() -> list[SearchProfile]:
    """Load all search profiles from environment configuration.

    Uses SearchProfile.load_all() which reads PROFILE_COUNT and PROFILE_N_
    variables or falls back to legacy SEARCH_QUERY mode.

    Returns:
        List of loaded SearchProfile instances.

    Raises:
        SystemExit: If no valid profile configuration is found.
    """
    try:
        return SearchProfile.load_all()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
