"""Unit tests for the Sighting domain model."""

from datetime import datetime

from src.core.domain.sighting import Sighting


def test_sighting_requires_platform_and_time():
    """A Sighting carries a platform and a timestamp; url is optional."""
    s = Sighting(platform="linkedin", seen_at=datetime(2026, 7, 14, 9, 0, 0))
    assert s.platform == "linkedin"
    assert s.url is None


def test_sighting_accepts_url():
    """A Sighting stores the platform-specific URL when given."""
    s = Sighting(
        platform="indeed",
        url="https://indeed.com/1",
        seen_at=datetime(2026, 7, 14, 9, 0, 0),
    )
    assert s.url == "https://indeed.com/1"
