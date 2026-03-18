"""Unit tests for the LinkedIn scraper adapter."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.scrapers.linkedin import LinkedInScraper
from src.core.domain.job import Job


def make_mock_card(title: str, company: str, location: str, href: str):
    """Build a mock Playwright element simulating a LinkedIn job card."""
    title_el = AsyncMock()
    title_el.inner_text = AsyncMock(return_value=f"  {title}  ")

    company_el = AsyncMock()
    company_el.inner_text = AsyncMock(return_value=company)

    location_el = AsyncMock()
    location_el.inner_text = AsyncMock(return_value=location)

    link_el = AsyncMock()
    link_el.get_attribute = AsyncMock(return_value=href)

    card = AsyncMock()

    async def query_selector(selector):
        mapping = {
            ".base-search-card__title": title_el,
            ".base-search-card__subtitle": company_el,
            ".base-search-card__metadata": location_el,
            "a.base-card__full-link": link_el,
        }
        return mapping.get(selector)

    card.query_selector = query_selector
    return card


@pytest.fixture
def mock_playwright_context():
    """Return a fully mocked async_playwright context for LinkedIn tests."""
    description_el = AsyncMock()
    description_el.inner_text = AsyncMock(return_value="Python developer role.")

    page = AsyncMock()
    page.set_extra_http_headers = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock(return_value=description_el)
    page.query_selector_all = AsyncMock(return_value=[
        make_mock_card(
            title="Senior Python Developer",
            company="Acme Corp",
            location="Remote",
            href="https://linkedin.com/jobs/123",
        )
    ])

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
    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert len(results) == 1
    assert isinstance(results[0], Job)
    assert results[0].title == "Senior Python Developer"
    assert results[0].company == "Acme Corp"
    assert results[0].platform == "linkedin"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_timeout():
    """Error handling — returns empty list when page load times out."""
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))
    cm.__aexit__ = AsyncMock(return_value=False)

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=cm):
        results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_when_no_cards_found(mock_playwright_context):
    """Edge case — returns empty list when no job cards are present."""
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()
    page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeoutError("no cards"))

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_respects_limit(mock_playwright_context):
    """Happy path — fetch_jobs does not return more than limit results."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()
    page.query_selector_all = AsyncMock(return_value=[
        make_mock_card("Job A", "Co A", "Remote", "https://linkedin.com/1"),
        make_mock_card("Job B", "Co B", "Remote", "https://linkedin.com/2"),
        make_mock_card("Job C", "Co C", "Remote", "https://linkedin.com/3"),
    ])

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Python Developer", "Remote", limit=2)

    assert len(results) <= 2
