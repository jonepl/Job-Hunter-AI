"""Unit tests for SQLiteProfileRepository over an in-memory store (W7)."""

from src.adapters.repository.sqlite_profile_repository import (
    SQLiteProfileRepository,
)
from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.domain.work_type import WorkType


def _repo() -> SQLiteProfileRepository:
    """Return a profile repository over a fresh in-memory database."""
    return SQLiteProfileRepository(db_path=":memory:")


def _profile(**overrides) -> SearchProfile:
    """Return a SearchProfile with sensible defaults and optional overrides."""
    fields = {
        "profile_id": 0,
        "name": "Backend",
        "query": "Senior Software Engineer",
        "location": "United States",
        "work_types": [WorkType.REMOTE],
        "date_posted": DatePosted.DAYS3,
        "active_scrapers": [ScraperName.LINKEDIN, ScraperName.INDEED],
        "score_threshold": 75,
        "top_results": None,
    }
    fields.update(overrides)
    return SearchProfile(**fields)


def test_create_assigns_id_and_round_trips_enums():
    """Create returns the row id; enum list columns round-trip through JSON."""
    repo = _repo()
    created = repo.create_profile(_profile())
    assert created.profile_id >= 1

    fetched = repo.get_profile(created.profile_id)
    assert fetched.name == "Backend"
    assert fetched.work_types == [WorkType.REMOTE]
    assert fetched.date_posted == DatePosted.DAYS3
    assert fetched.active_scrapers == [ScraperName.LINKEDIN, ScraperName.INDEED]


def test_none_work_types_and_top_results_persist_as_null():
    """A None work-type / top-results filter round-trips as None."""
    repo = _repo()
    created = repo.create_profile(_profile(work_types=None, top_results=None))
    fetched = repo.get_profile(created.profile_id)
    assert fetched.work_types is None
    assert fetched.top_results is None


def test_list_orders_by_position():
    """Profiles list in creation (position) order."""
    repo = _repo()
    repo.create_profile(_profile(name="First"))
    repo.create_profile(_profile(name="Second"))
    assert [p.name for p in repo.list_profiles()] == ["First", "Second"]


def test_update_persists_changes():
    """Update overwrites the stored fields."""
    repo = _repo()
    created = repo.create_profile(_profile())
    repo.update_profile(
        created.model_copy(update={"query": "Staff Engineer", "score_threshold": 80})
    )
    fetched = repo.get_profile(created.profile_id)
    assert fetched.query == "Staff Engineer"
    assert fetched.score_threshold == 80


def test_delete_and_count():
    """Delete removes a row; count reflects the store size."""
    repo = _repo()
    a = repo.create_profile(_profile(name="A"))
    repo.create_profile(_profile(name="B"))
    assert repo.count() == 2
    repo.delete_profile(a.profile_id)
    assert repo.count() == 1
    assert repo.get_profile(a.profile_id) is None
