"""Unit tests for the ScraperFactory build_scrapers function."""

from src.adapters.scrapers.jsearch import JSearchScraper
from src.adapters.scrapers.linkedin import LinkedInScraper
from src.adapters.scrapers.scraper_factory import build_scrapers
from src.core.domain.scraper_name import ScraperName


def test_build_scrapers_linkedin_only():
    """active=[LINKEDIN] returns a list with one LinkedInScraper instance."""
    result = build_scrapers([ScraperName.LINKEDIN])
    assert len(result) == 1
    assert isinstance(result[0], LinkedInScraper)


def test_build_scrapers_jsearch_platforms():
    """active=[INDEED, GLASSDOOR, ZIPRECRUITER] returns three JSearchScrapers
    with the correct platform labels."""
    result = build_scrapers(
        [
            ScraperName.INDEED,
            ScraperName.GLASSDOOR,
            ScraperName.ZIPRECRUITER,
        ]
    )
    assert len(result) == 3
    assert all(isinstance(s, JSearchScraper) for s in result)
    assert result[0].platform == "indeed"
    assert result[1].platform == "glassdoor"
    assert result[2].platform == "ziprecruiter"


def test_build_scrapers_all_four():
    """ScraperName.all() builds all four scrapers."""
    result = build_scrapers(ScraperName.all())
    assert len(result) == 4


def test_build_scrapers_preserves_order():
    """Output order matches input order — INDEED first, LINKEDIN second."""
    result = build_scrapers([ScraperName.INDEED, ScraperName.LINKEDIN])
    assert isinstance(result[0], JSearchScraper)
    assert result[0].platform == "indeed"
    assert isinstance(result[1], LinkedInScraper)


def test_build_scrapers_empty_list():
    """active=[] returns an empty list."""
    result = build_scrapers([])
    assert result == []
