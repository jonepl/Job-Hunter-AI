"""Unit tests for the Indeed scraper adapter."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.adapters.scrapers.indeed import IndeedScraper
from src.core.domain.job import Job

_SEARCH_HTML = """
<html><body>
<div data-jk="abc123">
    <h2><a data-testid="jobTitle"><span>Python Developer</span></a></h2>
    <span data-testid="company-name">Acme Corp</span>
    <div data-testid="text-location">Remote</div>
</div>
</body></html>
"""

_DETAIL_HTML = """
<html><body>
<div id="jobDescriptionText">
    We are looking for a Python Developer with 3+ years of experience.
</div>
</body></html>
"""


def make_mock_response(html: str, status: int = 200) -> MagicMock:
    """Build a mock requests.Response with the given HTML content."""
    mock = MagicMock()
    mock.text = html
    mock.status_code = status
    mock.raise_for_status = MagicMock()
    return mock


@pytest.mark.asyncio
async def test_fetch_jobs_returns_list_of_job_models():
    """Happy path — fetch_jobs returns validated Job Pydantic models."""
    scraper = IndeedScraper()
    responses = [make_mock_response(_SEARCH_HTML), make_mock_response(_DETAIL_HTML)]

    with patch("src.adapters.scrapers.indeed.requests.get", side_effect=responses):
        with patch("src.adapters.scrapers.indeed.asyncio.sleep"):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert len(results) == 1
    assert isinstance(results[0], Job)
    assert results[0].title == "Python Developer"
    assert results[0].company == "Acme Corp"
    assert results[0].platform == "indeed"
    assert "Python Developer" in results[0].description


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_timeout():
    """Error handling — returns empty list on requests.Timeout."""
    scraper = IndeedScraper()

    with patch("src.adapters.scrapers.indeed.requests.get", side_effect=requests.Timeout):
        with patch("src.adapters.scrapers.indeed.asyncio.sleep"):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_http_error():
    """Error handling — returns empty list on HTTP error response."""
    scraper = IndeedScraper()
    mock_response = make_mock_response("", status=403)
    mock_response.raise_for_status = MagicMock(side_effect=requests.HTTPError("403"))

    with patch("src.adapters.scrapers.indeed.requests.get", return_value=mock_response):
        with patch("src.adapters.scrapers.indeed.asyncio.sleep"):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_when_no_cards_in_html():
    """Edge case — returns empty list when HTML contains no job cards."""
    scraper = IndeedScraper()

    with patch("src.adapters.scrapers.indeed.requests.get",
               return_value=make_mock_response("<html><body>No jobs here.</body></html>")):
        with patch("src.adapters.scrapers.indeed.asyncio.sleep"):
            results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results == []
