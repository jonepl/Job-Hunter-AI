"""Unit tests for the ZipRecruiter scraper adapter."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.adapters.scrapers.ziprecruiter import ZipRecruiterScraper
from src.core.domain.job import Job

_SEARCH_HTML = """
<html><body>
<article data-job-id="zr001">
    <a class="job_title" href="https://www.ziprecruiter.com/jobs/acme-123">
        DevOps Engineer
    </a>
    <a class="hiring_company_text">Acme Corp</a>
    <p class="location">Miami, FL</p>
    <a href="https://www.ziprecruiter.com/jobs/acme-123">View Job</a>
</article>
</body></html>
"""

_DETAIL_HTML = """
<html><body>
<div class="job_description">
    We are seeking a DevOps Engineer with Kubernetes experience.
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
    scraper = ZipRecruiterScraper()
    responses = [make_mock_response(_SEARCH_HTML), make_mock_response(_DETAIL_HTML)]

    with patch("src.adapters.scrapers.ziprecruiter.requests.get", side_effect=responses):
        with patch("src.adapters.scrapers.ziprecruiter.asyncio.sleep"):
            results = await scraper.fetch_jobs("DevOps Engineer", "Miami, FL")

    assert len(results) >= 1
    assert isinstance(results[0], Job)
    assert results[0].platform == "ziprecruiter"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_timeout():
    """Error handling — returns empty list on requests.Timeout."""
    scraper = ZipRecruiterScraper()

    with patch("src.adapters.scrapers.ziprecruiter.requests.get", side_effect=requests.Timeout):
        with patch("src.adapters.scrapers.ziprecruiter.asyncio.sleep"):
            results = await scraper.fetch_jobs("DevOps Engineer", "Miami, FL")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_http_error():
    """Error handling — returns empty list on HTTP error response."""
    scraper = ZipRecruiterScraper()
    mock_response = make_mock_response("", status=403)
    mock_response.raise_for_status = MagicMock(side_effect=requests.HTTPError("403"))

    with patch("src.adapters.scrapers.ziprecruiter.requests.get", return_value=mock_response):
        with patch("src.adapters.scrapers.ziprecruiter.asyncio.sleep"):
            results = await scraper.fetch_jobs("DevOps Engineer", "Miami, FL")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_when_no_cards_in_html():
    """Edge case — returns empty list when HTML contains no job cards."""
    scraper = ZipRecruiterScraper()

    with patch("src.adapters.scrapers.ziprecruiter.requests.get",
               return_value=make_mock_response("<html><body>No jobs here.</body></html>")):
        with patch("src.adapters.scrapers.ziprecruiter.asyncio.sleep"):
            results = await scraper.fetch_jobs("DevOps Engineer", "Miami, FL")

    assert results == []
