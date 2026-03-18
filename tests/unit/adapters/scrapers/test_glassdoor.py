"""Unit tests for the Glassdoor scraper adapter."""

from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.scrapers.glassdoor import GlassdoorScraper
from src.core.domain.job import Job


def make_mock_card(title: str, company: str, location: str, href: str):
    """Build a mock Playwright element simulating a Glassdoor job card."""
    title_el = AsyncMock()
    title_el.inner_text = AsyncMock(return_value=title)

    company_el = AsyncMock()
    company_el.inner_text = AsyncMock(return_value=company)

    location_el = AsyncMock()
    location_el.inner_text = AsyncMock(return_value=location)

    link_el = AsyncMock()
    link_el.get_attribute = AsyncMock(return_value=href)

    card = AsyncMock()

    async def query_selector(selector):
        mapping = {
            "[data-test='job-title']": title_el,
            "[data-test='employer-name']": company_el,
            "[data-test='emp-location']": location_el,
            "a[data-test='job-title']": link_el,
        }
        return mapping.get(selector)

    card.query_selector = query_selector
    card.click = AsyncMock()
    return card


@pytest.fixture
def mock_playwright_context():
    """Return a fully mocked async_playwright context for Glassdoor tests."""
    description_el = AsyncMock()
    description_el.inner_text = AsyncMock(return_value="Data engineer role.")

    page = AsyncMock()
    page.set_extra_http_headers = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)  # no close button
    page.query_selector_all = AsyncMock(return_value=[
        make_mock_card(
            title="Senior Data Engineer",
            company="TechCorp",
            location="Remote",
            href="/jobs/view/123",
        )
    ])

    # Second call to query_selector returns description element
    page.query_selector.side_effect = [
        None,  # close button check
        description_el,  # description extraction
    ]

    browser = AsyncMock()
    browser.new_page = AsyncMock(return_value=page)
    browser.close = AsyncMock()

    chromium = AsyncMock()
    chromium.launch = AsyncMock(return_value=browser)

    playwright_instance = AsyncMock()
    playwright_instance.chromium = chromium

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=playwright_instance)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_fetch_jobs_returns_list_of_job_models(mock_playwright_context):
    """Happy path — fetch_jobs returns validated Job Pydantic models."""
    scraper = GlassdoorScraper()
    with patch("src.adapters.scrapers.glassdoor.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.glassdoor.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Data Engineer", "Remote")

    assert len(results) == 1
    assert isinstance(results[0], Job)
    assert results[0].title == "Senior Data Engineer"
    assert results[0].platform == "glassdoor"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_timeout():
    """Error handling — returns empty list when page load times out."""
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))
    cm.__aexit__ = AsyncMock(return_value=False)

    scraper = GlassdoorScraper()
    with patch("src.adapters.scrapers.glassdoor.async_playwright", return_value=cm):
        results = await scraper.fetch_jobs("Data Engineer", "Remote")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_when_no_cards_found(mock_playwright_context):
    """Edge case — returns empty list when no job cards are present."""
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()
    page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeoutError("no cards"))

    scraper = GlassdoorScraper()
    with patch("src.adapters.scrapers.glassdoor.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.glassdoor.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Data Engineer", "Remote")

    assert results == []
