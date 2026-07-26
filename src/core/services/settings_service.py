"""SettingsService — the DB-backed configuration layer (W7, ADR-031).

``.env`` is a bootstrap **seed**: on first access the global operational settings and
the search profiles are copied from the environment into the SQLite store, which is
authoritative thereafter. Runs read their config from here (via the env bridge below);
the browser Settings screen edits it.

**Secrets are handled specially.** API-key values are *not* seeded into the DB — the
``.env`` value stays the fallback default. A secret is stored in the DB only when the
user explicitly replaces it, and the value is **never returned** to a caller: only a
masked suffix, a ``configured`` flag, and an ``overridden`` flag (DB value present and
differing from the live ``.env`` value) leave the service (ADR-031).

**The env bridge (ADR-035).** Every existing factory/adapter reads config from
``os.getenv``. Rather than refactor them, ``apply_to_environment`` writes the effective
DB settings + secret overrides back into ``os.environ`` at each run start, so the
factories transparently read the current configuration. Search profiles are the one
path read directly from the DB (``list_profiles``), not through the environment.
"""

import logging
import os
from datetime import datetime

import pytz
from apscheduler.triggers.cron import CronTrigger

from src.core.domain.app_settings import AppSettings
from src.core.domain.search_profile import SearchProfile
from src.core.domain.voice_descriptor import VoiceDescriptor
from src.core.ports.profile_repository_port import ProfileRepositoryPort
from src.core.ports.settings_repository_port import SettingsRepositoryPort

logger = logging.getLogger(__name__)

_SEEDED_KEY = "_seeded"

# Global (non-secret) setting key → the .env variable it seeds from / bridges to.
_GLOBAL_ENV = {
    "evaluator_provider": "EVALUATOR_PROVIDER",
    "evaluator_model": "EVALUATOR_MODEL",
    "enrichment_mode": "ENRICHMENT_MODE",
    "voice_tone": "VOICE_TONE",
    "voice_person": "VOICE_PERSON",
    "voice_style_notes": "VOICE_STYLE_NOTES",
}

# Secret name → the .env variable it overrides. Never seeded into the DB; the .env
# value is the fallback default until the user explicitly replaces it.
_SECRET_ENV = {
    "openai_api_key": "OPENAI_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "gemini_api_key": "GEMINI_API_KEY",
}

_DEFAULTS = {
    "evaluator_provider": "openai",
    "evaluator_model": "",
    "enrichment_mode": "shadow",
    "voice_tone": "direct",
    "voice_person": "first_person",
    "voice_style_notes": "",
}

SECRET_NAMES = tuple(_SECRET_ENV.keys())


class SettingsService:
    """Read/write the global settings, secrets, and search profiles (ADR-031)."""

    def __init__(
        self,
        settings_repo: SettingsRepositoryPort,
        profile_repo: ProfileRepositoryPort,
    ) -> None:
        """Wire the settings and profile repositories.

        Args:
            settings_repo: The key/value settings store.
            profile_repo: The search-profile store.
        """
        self._settings = settings_repo
        self._profiles = profile_repo

    # --- global settings ---------------------------------------------------

    def get_settings(self) -> AppSettings:
        """Return the effective global settings, seeding from ``.env`` if empty."""
        self._seed_if_empty()
        values = {**_DEFAULTS, **self._settings.get_all()}
        return _to_settings(values)

    def update_settings(self, settings: AppSettings) -> AppSettings:
        """Persist the non-secret global settings and return them."""
        self._seed_if_empty()
        for key, value in _from_settings(settings).items():
            self._settings.set(key, value)
        logger.info("Updated global settings (provider=%s)", settings.evaluator_provider)
        return self.get_settings()

    def env_defaults(self) -> AppSettings:
        """Return the settings as derived purely from ``.env`` (for the UI diff)."""
        values = {key: os.getenv(env, "") for key, env in _GLOBAL_ENV.items()}
        merged = {**_DEFAULTS, **{k: v for k, v in values.items() if v}}
        return _to_settings(merged)

    # --- secrets (write-only, never returned) ------------------------------

    def secret_status(self, name: str) -> dict:
        """Return a secret's masked status — never its value (ADR-031).

        Args:
            name: One of ``SECRET_NAMES``.

        Returns:
            ``{name, configured, masked, overridden}``. ``configured`` is true when a
            value exists in the DB or ``.env``; ``overridden`` is true when the DB
            holds a value differing from the live ``.env`` value; ``masked`` is the
            last-4 suffix of the effective value.
        """
        env_value = os.getenv(_SECRET_ENV[name], "")
        db_value = self._settings.get(name)
        effective = db_value if db_value else env_value
        return {
            "name": name,
            "configured": bool(effective),
            "masked": effective[-4:] if len(effective) >= 4 else "",
            "overridden": bool(db_value) and db_value != env_value,
        }

    def all_secret_statuses(self) -> list[dict]:
        """Return the masked status of every known secret."""
        return [self.secret_status(name) for name in SECRET_NAMES]

    def set_secret(self, name: str, value: str) -> None:
        """Store a DB override for a secret (the value never leaves the service)."""
        if name not in _SECRET_ENV:
            raise KeyError(name)
        self._settings.set(name, value)
        logger.info("Secret %s replaced via settings (write-only)", name)

    def clear_secret(self, name: str) -> None:
        """Remove a secret's DB override, reverting to the ``.env`` value."""
        if name not in _SECRET_ENV:
            raise KeyError(name)
        self._settings.delete(name)
        logger.info("Secret %s reset to .env default", name)

    # --- search profiles ---------------------------------------------------

    def list_profiles(self) -> list[SearchProfile]:
        """Return every stored profile, seeding from ``.env`` if empty."""
        self._seed_if_empty()
        return self._profiles.list_profiles()

    def get_profile(self, profile_id: int) -> SearchProfile | None:
        """Return one profile by id, or None when absent."""
        return self._profiles.get_profile(profile_id)

    def create_profile(self, profile: SearchProfile) -> SearchProfile:
        """Create a new search profile."""
        return self._profiles.create_profile(profile)

    def update_profile(self, profile: SearchProfile) -> SearchProfile:
        """Update an existing search profile."""
        return self._profiles.update_profile(profile)

    def delete_profile(self, profile_id: int) -> None:
        """Delete a search profile by id."""
        self._profiles.delete_profile(profile_id)

    def set_profile_last_run(self, profile_id: int, status: str, at: str) -> None:
        """Record a profile's most recent run outcome (pipeline-owned, Part B).

        Delegates to the repository's narrow ``set_last_run`` write so the run loops
        can stamp ``running`` → ``succeeded``/``failed`` without a full profile
        round-trip that could race a concurrent Settings edit.

        Args:
            profile_id: The profile whose run metadata to update.
            status: ``running`` | ``succeeded`` | ``failed``.
            at: ISO-8601 timestamp of the run start.
        """
        self._profiles.set_last_run(profile_id, status, at)

    def profile_count(self) -> int:
        """Return the number of stored profiles."""
        return self._profiles.count()

    # --- run integration ---------------------------------------------------

    def apply_to_environment(self) -> None:
        """Push the effective DB settings + secret overrides into ``os.environ``.

        The env bridge (ADR-035): existing factories read ``os.getenv``, so writing the
        current config here makes DB edits take effect at the next run/build without
        touching any adapter. Idempotent; only sets keys this service owns.
        """
        self._seed_if_empty()
        stored = self._settings.get_all()
        for key, env in _GLOBAL_ENV.items():
            if key in stored:
                os.environ[env] = stored[key]
        for name, env in _SECRET_ENV.items():
            if name in stored and stored[name]:
                os.environ[env] = stored[name]

    def next_run_times(self, cron: str, timezone: str = "UTC", n: int = 3) -> list[datetime]:
        """Return the next ``n`` fire times for a cron expression (no live scheduler).

        Args:
            cron: A 5-field crontab expression.
            timezone: The timezone to evaluate it in.
            n: How many upcoming times to return.

        Returns:
            The next ``n`` fire times, ascending.

        Raises:
            ValueError: When the cron expression or timezone is invalid.
        """
        tz = pytz.timezone(timezone)
        trigger = CronTrigger.from_crontab(cron, timezone=tz)
        times: list[datetime] = []
        previous = None
        now = datetime.now(tz)
        for _ in range(n):
            nxt = trigger.get_next_fire_time(previous, now)
            if nxt is None:
                break
            times.append(nxt)
            previous = nxt
            now = nxt
        return times

    # --- seeding -----------------------------------------------------------

    def _seed_if_empty(self) -> None:
        """Seed globals from ``.env`` and profiles from the loader, exactly once."""
        if self._settings.get(_SEEDED_KEY) is not None:
            return
        for key, env in _GLOBAL_ENV.items():
            value = os.getenv(env)
            if value is not None:
                self._settings.set(key, value)
        if self._profiles.count() == 0:
            for profile in _seed_profiles():
                self._profiles.create_profile(profile)
        self._settings.set(_SEEDED_KEY, "1")
        logger.info("Seeded settings + profiles from .env (first run)")


def _to_settings(values: dict) -> AppSettings:
    """Build an AppSettings from a flat ``{key: str}`` mapping."""
    return AppSettings(
        evaluator_provider=values.get("evaluator_provider") or "openai",
        evaluator_model=(values.get("evaluator_model") or None),
        enrichment_mode=values.get("enrichment_mode") or "shadow",
        voice=VoiceDescriptor(
            tone=values.get("voice_tone") or "direct",
            person=values.get("voice_person") or "first_person",
            style_notes=values.get("voice_style_notes", ""),
        ),
    )


def _from_settings(settings: AppSettings) -> dict[str, str]:
    """Flatten an AppSettings into the ``{key: str}`` mapping the store persists."""
    return {
        "evaluator_provider": settings.evaluator_provider,
        "evaluator_model": settings.evaluator_model or "",
        "enrichment_mode": settings.enrichment_mode,
        "voice_tone": settings.voice.tone,
        "voice_person": settings.voice.person,
        "voice_style_notes": settings.voice.style_notes,
    }


def _seed_profiles() -> list[SearchProfile]:
    """Load profiles from ``.env`` for seeding; empty when none are configured."""
    try:
        return SearchProfile.load_all()
    except (ValueError, SystemExit):
        return []
