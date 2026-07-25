"""Application bootstrap for the Job Hunter AI Agent.

Loads the search profiles the run pipeline iterates. Contains no CLI or API
dependency — accepts plain Python objects so it is reused by both the CLI
entrypoint and the API.

Profiles now live in the DB (W7, ADR-031): ``SettingsService`` seeds them from
``.env`` on first run and is authoritative thereafter, so the loader reads the
store instead of the environment directly.
"""

import sys

from src.core.domain.search_profile import SearchProfile
from src.orchestration.service_factory import build_settings_service


def load_profiles() -> list[SearchProfile]:
    """Load all search profiles from the DB-backed store (seeded from ``.env``).

    Returns:
        List of stored SearchProfile instances.

    Raises:
        SystemExit: When no profiles are configured (neither in the DB nor ``.env``).
    """
    profiles = build_settings_service().list_profiles()
    if not profiles:
        print(
            "Error: no search profiles configured. Set PROFILE_COUNT/PROFILE_N_* "
            "(or SEARCH_QUERY) in .env, or add a profile in the web Settings."
        )
        sys.exit(1)
    return profiles
