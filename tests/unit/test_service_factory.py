"""Unit tests for service_factory.build_service() — pre-filter wiring."""

from unittest.mock import MagicMock, patch

from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.service_factory import build_service


def _profile() -> SearchProfile:
    """Return a minimal SearchProfile for factory tests."""
    return SearchProfile(
        profile_id=1,
        query="Engineer",
        location="Remote",
        active_scrapers=[ScraperName.LINKEDIN],
        score_threshold=75,
        date_posted=DatePosted.DAYS3,
    )


def test_build_service_wires_enrichment_and_mode(monkeypatch):
    """build_service injects the pre-filter and enforce mode into the service."""
    monkeypatch.setenv("ENRICHMENT_MODE", "enforce")
    sentinel = MagicMock()

    with patch("src.service_factory.build_scrapers", return_value=[MagicMock()]), \
         patch("src.service_factory.build_evaluator", return_value=MagicMock()), \
         patch("src.service_factory.build_enrichment", return_value=sentinel):
        service = build_service(_profile())

    assert service._enrichment is sentinel
    assert service._enrichment_mode == "enforce"


def test_build_service_defaults_mode_to_shadow(monkeypatch):
    """An unset ENRICHMENT_MODE defaults to shadow."""
    monkeypatch.delenv("ENRICHMENT_MODE", raising=False)

    with patch("src.service_factory.build_scrapers", return_value=[MagicMock()]), \
         patch("src.service_factory.build_evaluator", return_value=MagicMock()), \
         patch("src.service_factory.build_enrichment", return_value=None):
        service = build_service(_profile())

    assert service._enrichment is None
    assert service._enrichment_mode == "shadow"


def test_build_service_normalizes_invalid_mode(monkeypatch):
    """An unrecognised ENRICHMENT_MODE falls back to shadow."""
    monkeypatch.setenv("ENRICHMENT_MODE", "banana")

    with patch("src.service_factory.build_scrapers", return_value=[MagicMock()]), \
         patch("src.service_factory.build_evaluator", return_value=MagicMock()), \
         patch("src.service_factory.build_enrichment", return_value=None):
        service = build_service(_profile())

    assert service._enrichment_mode == "shadow"
