"""Unit tests for the LinkedIn scraper adapter."""

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.scrapers.linkedin import LinkedInScraper
from src.core.domain.date_posted import DatePosted
from src.core.domain.job import Job
from src.core.domain.work_type import WorkType


def make_mock_card(title: str, company: str, location: str, href: str, posted: str | None = None):
    """Build a mock Playwright element simulating a LinkedIn job card.

    ``posted`` is the ISO ``datetime`` attribute on the card's ``<time>`` element;
    when None the ``<time>`` selector resolves to nothing (posting age unknown).
    """
    title_el = AsyncMock()
    title_el.inner_text = AsyncMock(return_value=f"  {title}  ")

    company_el = AsyncMock()
    company_el.inner_text = AsyncMock(return_value=company)

    location_el = AsyncMock()
    location_el.inner_text = AsyncMock(return_value=location)

    link_el = AsyncMock()
    link_el.get_attribute = AsyncMock(return_value=href)

    time_el = None
    if posted is not None:
        time_el = AsyncMock()
        time_el.get_attribute = AsyncMock(return_value=posted)

    card = AsyncMock()

    async def query_selector(selector):
        mapping = {
            ".base-search-card__title": title_el,
            ".base-search-card__subtitle": company_el,
            ".base-search-card__metadata": location_el,
            "a.base-card__full-link": link_el,
            ".base-search-card__metadata time": time_el,
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
async def test_fetch_jobs_parses_posted_at_from_time_element(mock_playwright_context):
    """posted_at is read from the card's <time datetime="…"> attribute (A.4)."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()
    page.query_selector_all = AsyncMock(return_value=[
        make_mock_card("SE", "Acme", "Remote", "https://linkedin.com/1",
                       posted="2026-07-15"),
    ])

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results[0].posted_at == datetime(2026, 7, 15)


@pytest.mark.asyncio
async def test_fetch_jobs_leaves_salary_and_employment_none(mock_playwright_context):
    """LinkedIn never exposes salary/employment type — they stay None."""
    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    job = results[0]
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert job.salary_period is None
    assert job.employment_type is None


@pytest.mark.asyncio
async def test_fetch_jobs_missing_time_element_yields_none_posted_at(mock_playwright_context):
    """A card without a <time> element degrades posted_at to None, not an error."""
    # The default mock card carries no <time> (posted=None).
    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results[0].posted_at is None


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


@pytest.mark.asyncio
async def test_fetch_jobs_all_cards_parsed_despite_navigation(mock_playwright_context):
    """Regression — all cards are parsed even though _fetch_description navigates away.

    Simulates the stale-handle scenario: page.goto is called once per card during
    Pass 2 (description fetching). All card fields must still be present because
    they were collected in Pass 1, before any navigation occurred.
    """
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()
    page.query_selector_all = AsyncMock(return_value=[
        make_mock_card("Job A", "Co A", "NYC", "https://linkedin.com/1"),
        make_mock_card("Job B", "Co B", "Remote", "https://linkedin.com/2"),
        make_mock_card("Job C", "Co C", "Austin", "https://linkedin.com/3"),
    ])

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert len(results) == 3
    titles = [r.title for r in results]
    assert "Job A" in titles
    assert "Job B" in titles
    assert "Job C" in titles


@pytest.mark.asyncio
async def test_fetch_jobs_description_navigation_called_after_all_cards_parsed(mock_playwright_context):
    """Regression — page.goto for descriptions is only called after Pass 1 completes.

    Verifies that card.query_selector is never called after page.goto fires,
    confirming the two-pass order is preserved.
    """
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    cards = [
        make_mock_card("Job X", "Co X", "Remote", "https://linkedin.com/x"),
        make_mock_card("Job Y", "Co Y", "Remote", "https://linkedin.com/y"),
    ]
    page.query_selector_all = AsyncMock(return_value=cards)

    call_log: list[str] = []

    original_goto = page.goto.side_effect

    async def tracked_goto(url, **kwargs):
        call_log.append(f"goto:{url}")

    page.goto = AsyncMock(side_effect=tracked_goto)

    for card in cards:
        original_qs = card.query_selector

        async def tracked_qs(selector, _orig=original_qs):
            call_log.append(f"card_qs:{selector}")
            return await _orig(selector)

        card.query_selector = tracked_qs

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs("Python Developer", "Remote")

    # All card.query_selector calls must appear before any description-fetch
    # page.goto calls. The initial search-page goto is excluded — only navigations
    # to the job detail URLs (collected in Pass 2) count here.
    detail_urls = {"https://linkedin.com/x", "https://linkedin.com/y"}
    first_detail_goto = next(
        (i for i, e in enumerate(call_log) if e.startswith("goto:") and e[5:] in detail_urls),
        len(call_log),
    )
    last_card_qs = next(
        (i for i, e in reversed(list(enumerate(call_log))) if e.startswith("card_qs:")),
        -1,
    )
    assert last_card_qs < first_detail_goto, (
        "card.query_selector was called after page.goto — stale-handle bug reintroduced"
    )


# ---------------------------------------------------------------------------
# Work type filter — URL and logging
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_remote_filter_added_to_url(mock_playwright_context):
    """work_types=[REMOTE] → f_WT=2 is present in the navigated search URL."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs("SE", "Remote", work_types=[WorkType.REMOTE])

    search_url = page.goto.call_args_list[0][0][0]
    assert "f_WT=2" in search_url


@pytest.mark.asyncio
async def test_hybrid_filter_added_to_url(mock_playwright_context):
    """work_types=[HYBRID] → f_WT=3 is present in the navigated search URL."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs("SE", "New York", work_types=[WorkType.HYBRID])

    search_url = page.goto.call_args_list[0][0][0]
    assert "f_WT=3" in search_url


@pytest.mark.asyncio
async def test_onsite_filter_added_to_url(mock_playwright_context):
    """work_types=[ONSITE] → f_WT=1 is present in the navigated search URL."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs("SE", "Austin, TX", work_types=[WorkType.ONSITE])

    search_url = page.goto.call_args_list[0][0][0]
    assert "f_WT=1" in search_url


@pytest.mark.asyncio
async def test_multiple_work_types_in_url(mock_playwright_context):
    """work_types=[REMOTE, HYBRID] → both f_WT=2 and f_WT=3 appear in the search URL."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs(
                "SE", "New York", work_types=[WorkType.REMOTE, WorkType.HYBRID]
            )

    search_url = page.goto.call_args_list[0][0][0]
    assert "f_WT=2" in search_url
    assert "f_WT=3" in search_url


@pytest.mark.asyncio
async def test_no_work_type_filter_omits_f_wt(mock_playwright_context):
    """work_types=None → f_WT is not present in the navigated search URL."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs("SE", "Remote", work_types=None)

    search_url = page.goto.call_args_list[0][0][0]
    assert "f_WT" not in search_url


@pytest.mark.asyncio
async def test_no_work_type_logs_no_filter_message(mock_playwright_context, caplog):
    """work_types=None → INFO log contains 'no work type filter'."""
    scraper = LinkedInScraper()
    with caplog.at_level(logging.INFO, logger="src.adapters.scrapers.linkedin"):
        with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
            with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
                await scraper.fetch_jobs("SE", "Remote", work_types=None)

    assert any("no work type filter" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_remote_work_type_logs_filter_applied(mock_playwright_context, caplog):
    """work_types=[REMOTE] → INFO log contains 'remote'."""
    scraper = LinkedInScraper()
    with caplog.at_level(logging.INFO, logger="src.adapters.scrapers.linkedin"):
        with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
            with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
                await scraper.fetch_jobs("SE", "Remote", work_types=[WorkType.REMOTE])

    assert any("remote" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Date posted filter — URL and logging
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_date_posted_filter_added_to_url(mock_playwright_context):
    """date_posted=DAYS3 → f_TPR=r259200 is present in the navigated search URL."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs("SE", "Remote", date_posted=DatePosted.DAYS3)

    search_url = page.goto.call_args_list[0][0][0]
    assert "f_TPR=r259200" in search_url


@pytest.mark.asyncio
async def test_date_posted_week_added_to_url(mock_playwright_context):
    """date_posted=WEEK → f_TPR=r604800 is present in the navigated search URL."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs("SE", "Remote", date_posted=DatePosted.WEEK)

    search_url = page.goto.call_args_list[0][0][0]
    assert "f_TPR=r604800" in search_url


@pytest.mark.asyncio
async def test_no_date_posted_omits_f_tpr(mock_playwright_context):
    """date_posted=None → f_TPR is not present in the navigated search URL."""
    playwright_instance = await mock_playwright_context.__aenter__()
    browser = await playwright_instance.chromium.launch()
    page = await browser.new_page()

    scraper = LinkedInScraper()
    with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
        with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
            await scraper.fetch_jobs("SE", "Remote", date_posted=None)

    search_url = page.goto.call_args_list[0][0][0]
    assert "f_TPR" not in search_url


@pytest.mark.asyncio
async def test_date_posted_logged_when_set(mock_playwright_context, caplog):
    """date_posted=DAYS3 → INFO log contains '3days'."""
    scraper = LinkedInScraper()
    with caplog.at_level(logging.INFO, logger="src.adapters.scrapers.linkedin"):
        with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
            with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
                await scraper.fetch_jobs("SE", "Remote", date_posted=DatePosted.DAYS3)

    assert any("3days" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_no_date_posted_logged_when_not_set(mock_playwright_context, caplog):
    """date_posted=None → INFO log contains 'no date posted filter'."""
    scraper = LinkedInScraper()
    with caplog.at_level(logging.INFO, logger="src.adapters.scrapers.linkedin"):
        with patch("src.adapters.scrapers.linkedin.async_playwright", return_value=mock_playwright_context):
            with patch("src.adapters.scrapers.linkedin.asyncio.sleep", new_callable=AsyncMock):
                await scraper.fetch_jobs("SE", "Remote", date_posted=None)

    assert any("no date posted filter" in record.message for record in caplog.records)
