"""Unit tests for SearchProfile domain model."""

import pytest

from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.domain.work_type import WorkType


class TestFromEnv:
    """Tests for SearchProfile.from_env()."""

    def test_from_env_loads_required_fields(self, monkeypatch):
        """from_env() loads query and location when both are set."""
        monkeypatch.setenv("PROFILE_1_QUERY", "Senior Software Engineer")
        monkeypatch.setenv("PROFILE_1_LOCATION", "New York")

        profile = SearchProfile.from_env(1)

        assert profile.query == "Senior Software Engineer"
        assert profile.location == "New York"
        assert profile.profile_id == 1

    def test_from_env_defaults_location_for_remote(self, monkeypatch):
        """from_env() defaults location to 'United States' when work type is remote only."""
        monkeypatch.setenv("PROFILE_1_QUERY", "Senior Software Engineer")
        monkeypatch.setenv("PROFILE_1_WORK_TYPE", "remote")
        monkeypatch.delenv("PROFILE_1_LOCATION", raising=False)

        profile = SearchProfile.from_env(1)

        assert profile.location == "United States"

    def test_from_env_raises_when_query_missing(self, monkeypatch):
        """from_env() raises ValueError when PROFILE_N_QUERY is not set."""
        monkeypatch.delenv("PROFILE_1_QUERY", raising=False)

        with pytest.raises(ValueError, match="PROFILE_1_QUERY is required"):
            SearchProfile.from_env(1)

    def test_from_env_raises_when_location_missing(self, monkeypatch):
        """from_env() raises ValueError when location is missing for non-remote work type."""
        monkeypatch.setenv("PROFILE_1_QUERY", "Full Stack Engineer")
        monkeypatch.setenv("PROFILE_1_WORK_TYPE", "hybrid")
        monkeypatch.delenv("PROFILE_1_LOCATION", raising=False)

        with pytest.raises(ValueError, match="PROFILE_1_LOCATION is required"):
            SearchProfile.from_env(1)

    def test_from_env_defaults_date_posted_to_3days(self, monkeypatch):
        """from_env() defaults date_posted to DatePosted.DAYS3 when not set."""
        monkeypatch.setenv("PROFILE_1_QUERY", "Senior Software Engineer")
        monkeypatch.setenv("PROFILE_1_LOCATION", "United States")
        monkeypatch.delenv("PROFILE_1_DATE_POSTED", raising=False)

        profile = SearchProfile.from_env(1)

        assert profile.date_posted == DatePosted.DAYS3

    def test_from_env_defaults_all_scrapers(self, monkeypatch):
        """from_env() defaults active_scrapers to all four platforms when not set."""
        monkeypatch.setenv("PROFILE_1_QUERY", "Senior Software Engineer")
        monkeypatch.setenv("PROFILE_1_LOCATION", "United States")
        monkeypatch.delenv("PROFILE_1_SCRAPERS", raising=False)

        profile = SearchProfile.from_env(1)

        assert ScraperName.LINKEDIN in profile.active_scrapers
        assert ScraperName.INDEED in profile.active_scrapers
        assert ScraperName.GLASSDOOR in profile.active_scrapers
        assert ScraperName.ZIPRECRUITER in profile.active_scrapers
        assert len(profile.active_scrapers) == 4

    def test_from_env_defaults_score_threshold_75(self, monkeypatch):
        """from_env() defaults score_threshold to 75 when not set."""
        monkeypatch.setenv("PROFILE_1_QUERY", "Senior Software Engineer")
        monkeypatch.setenv("PROFILE_1_LOCATION", "United States")
        monkeypatch.delenv("PROFILE_1_SCORE_THRESHOLD", raising=False)

        profile = SearchProfile.from_env(1)

        assert profile.score_threshold == 75

    def test_from_env_top_results_none_when_not_set(self, monkeypatch):
        """from_env() sets top_results to None when PROFILE_N_TOP_RESULTS is not set."""
        monkeypatch.setenv("PROFILE_1_QUERY", "Senior Software Engineer")
        monkeypatch.setenv("PROFILE_1_LOCATION", "United States")
        monkeypatch.delenv("PROFILE_1_TOP_RESULTS", raising=False)

        profile = SearchProfile.from_env(1)

        assert profile.top_results is None


class TestLoadAll:
    """Tests for SearchProfile.load_all()."""

    def test_load_all_with_profile_count(self, monkeypatch):
        """load_all() returns one profile per PROFILE_COUNT entry."""
        monkeypatch.setenv("PROFILE_COUNT", "2")
        monkeypatch.setenv("PROFILE_1_QUERY", "Senior Software Engineer")
        monkeypatch.setenv("PROFILE_1_LOCATION", "United States")
        monkeypatch.setenv("PROFILE_2_QUERY", "Full Stack Engineer")
        monkeypatch.setenv("PROFILE_2_LOCATION", "New York")
        monkeypatch.delenv("SEARCH_QUERY", raising=False)

        profiles = SearchProfile.load_all()

        assert len(profiles) == 2
        assert profiles[0].query == "Senior Software Engineer"
        assert profiles[1].query == "Full Stack Engineer"

    def test_load_all_legacy_fallback(self, monkeypatch):
        """load_all() falls back to legacy SEARCH_QUERY mode when PROFILE_COUNT is not set."""
        monkeypatch.delenv("PROFILE_COUNT", raising=False)
        monkeypatch.setenv("SEARCH_QUERY", "Senior Python Developer")
        monkeypatch.setenv("SEARCH_LOCATION", "Remote")

        profiles = SearchProfile.load_all()

        assert len(profiles) == 1
        assert profiles[0].query == "Senior Python Developer"
        assert profiles[0].profile_id == 1

    def test_load_all_raises_when_nothing_set(self, monkeypatch):
        """load_all() raises ValueError when neither PROFILE_COUNT nor SEARCH_QUERY is set."""
        monkeypatch.delenv("PROFILE_COUNT", raising=False)
        monkeypatch.delenv("SEARCH_QUERY", raising=False)

        with pytest.raises(ValueError, match="SEARCH_QUERY must be set"):
            SearchProfile.load_all()
