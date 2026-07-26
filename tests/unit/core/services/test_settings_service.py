"""Unit tests for SettingsService — seeding, secrets, env bridge, profiles (W7)."""

from src.adapters.repository.sqlite_profile_repository import (
    SQLiteProfileRepository,
)
from src.adapters.repository.sqlite_settings_repository import (
    SQLiteSettingsRepository,
)
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.services.settings_service import SettingsService


def _service() -> SettingsService:
    """Return a SettingsService over fresh in-memory repositories."""
    return SettingsService(
        SQLiteSettingsRepository(db_path=":memory:"),
        SQLiteProfileRepository(db_path=":memory:"),
    )


def _profile(**overrides) -> SearchProfile:
    """Return a minimal SearchProfile for CRUD tests."""
    fields = {
        "profile_id": 0,
        "name": "Backend",
        "query": "SWE",
        "location": "United States",
        "active_scrapers": [ScraperName.LINKEDIN],
        "score_threshold": 75,
    }
    fields.update(overrides)
    return SearchProfile(**fields)


def test_get_settings_seeds_globals_from_env(monkeypatch):
    """First read seeds the global settings from .env."""
    monkeypatch.setenv("EVALUATOR_PROVIDER", "anthropic")
    monkeypatch.setenv("ENRICHMENT_MODE", "enforce")
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)

    settings = _service().get_settings()
    assert settings.evaluator_provider == "anthropic"
    assert settings.enrichment_mode == "enforce"


def test_seed_runs_once(monkeypatch):
    """A change made after seeding is not clobbered by a re-seed."""
    monkeypatch.setenv("EVALUATOR_PROVIDER", "openai")
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)
    svc = _service()
    svc.get_settings()  # seeds
    monkeypatch.setenv("EVALUATOR_PROVIDER", "anthropic")  # .env changes later
    # A second read must not re-seed over the stored value.
    assert svc.get_settings().evaluator_provider == "openai"


def test_secret_status_masks_and_never_leaks(monkeypatch):
    """secret_status reports a masked suffix + flags, never the value."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-ABCD1234")
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)
    svc = _service()

    status = svc.secret_status("openai_api_key")
    assert status["configured"] is True
    assert status["masked"] == "1234"
    assert status["overridden"] is False
    assert "sk-env-ABCD1234" not in str(status)


def test_set_and_clear_secret_flips_overridden(monkeypatch):
    """A DB override flips overridden true; clearing reverts to the .env value."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-ABCD1234")
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)
    svc = _service()

    svc.set_secret("openai_api_key", "sk-db-WXYZ9999")
    overridden = svc.secret_status("openai_api_key")
    assert overridden["overridden"] is True
    assert overridden["masked"] == "9999"

    svc.clear_secret("openai_api_key")
    reverted = svc.secret_status("openai_api_key")
    assert reverted["overridden"] is False
    assert reverted["masked"] == "1234"


def test_apply_to_environment_bridges_db_values(monkeypatch):
    """apply_to_environment writes effective settings into os.environ."""
    monkeypatch.setenv("EVALUATOR_PROVIDER", "openai")
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)
    svc = _service()
    svc.update_settings(svc.get_settings().model_copy(update={"evaluator_provider": "anthropic"}))

    monkeypatch.setenv("EVALUATOR_PROVIDER", "WRONG")
    svc.apply_to_environment()
    import os

    assert os.environ["EVALUATOR_PROVIDER"] == "anthropic"


def test_apply_to_environment_bridges_secret_override(monkeypatch):
    """A secret override is applied to os.environ; the .env value stays otherwise."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-0000")
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)
    svc = _service()
    svc.set_secret("openai_api_key", "sk-db-1111")

    svc.apply_to_environment()
    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-db-1111"


def test_next_run_times_returns_three_ascending(monkeypatch):
    """next_run_times returns three ascending fire times for a valid cron."""
    times = _service().next_run_times("0 9 * * *", "UTC", n=3)
    assert len(times) == 3
    assert times[0] < times[1] < times[2]


def test_profile_crud(monkeypatch):
    """create / update / delete round-trip through the service."""
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)
    svc = _service()
    svc.list_profiles()  # seed (no profiles in env → empty)

    created = svc.create_profile(_profile(name="Backend"))
    assert svc.profile_count() == 1
    svc.update_profile(created.model_copy(update={"name": "Renamed"}))
    assert svc.get_profile(created.profile_id).name == "Renamed"
    svc.delete_profile(created.profile_id)
    assert svc.profile_count() == 0
