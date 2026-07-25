"""Unit tests for the ScraperPort abstract interface."""

import pytest

from src.core.domain.job import Job
from src.core.ports.scraper_port import ScraperPort


class ConcreteScraperPort(ScraperPort):
    """Minimal concrete implementation of ScraperPort for testing."""

    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
    ) -> list[Job]:
        """Return an empty list — implementation for testing only."""
        return []


class IncompleteScraperPort(ScraperPort):
    """Concrete subclass that omits the required abstract method."""

    pass


def test_scraper_port_concrete_implementation_instantiates():
    """Happy path — a complete implementation of ScraperPort can be instantiated."""
    scraper = ConcreteScraperPort()
    assert isinstance(scraper, ScraperPort)


def test_scraper_port_missing_implementation_raises_type_error():
    """Validation failure — subclass missing fetch_jobs raises TypeError."""
    with pytest.raises(TypeError):
        IncompleteScraperPort()


def test_scraper_port_fetch_jobs_signature_matches_contract():
    """Happy path — fetch_jobs accepts query, location, and optional limit."""
    import inspect

    sig = inspect.signature(ScraperPort.fetch_jobs)
    params = list(sig.parameters.keys())
    assert "query" in params
    assert "location" in params
    assert "limit" in params
    assert sig.parameters["limit"].default == 25
