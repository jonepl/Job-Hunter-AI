"""Unit tests for the JSearchScraper adapter."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.adapters.scrapers.jsearch import JSearchScraper
from src.core.domain.job import Job

_JSEARCH_RESPONSE = {
    "data": [
        {
            "job_title": "Python Developer",
            "employer_name": "Acme Corp",
            "job_city": "New York",
            "job_state": "NY",
            "job_apply_link": "https://example.com/jobs/123",
            "job_description": "We need a Python Developer with 3+ years of experience.",
            "job_posted_at_datetime_utc": "2026-03-18T00:00:00.000Z",
        }
    ]
}


def make_mock_response(payload: dict, status: int = 200) -> MagicMock:
    """Build a mock requests.Response with the given JSON payload."""
    mock = MagicMock()
    mock.status_code = status
    mock.raise_for_status = MagicMock()
    mock.json = MagicMock(return_value=payload)
    return mock


@pytest.mark.asyncio
async def test_fetch_jobs_returns_list_of_job_models():
    """Happy path — fetch_jobs returns validated Job Pydantic models."""
    scraper = JSearchScraper(platform="indeed")

    with patch("src.adapters.scrapers.jsearch.requests.get",
               return_value=make_mock_response(_JSEARCH_RESPONSE)):
        results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert len(results) == 1
    assert isinstance(results[0], Job)
    assert results[0].title == "Python Developer"
    assert results[0].company == "Acme Corp"
    assert results[0].location == "New York, NY"
    assert results[0].url == "https://example.com/jobs/123"
    assert "Python Developer" in results[0].description


@pytest.mark.asyncio
async def test_fetch_jobs_stamps_correct_platform_label():
    """Platform label — each instance stamps Job.platform with its platform value."""
    indeed_scraper = JSearchScraper(platform="indeed")
    glassdoor_scraper = JSearchScraper(platform="glassdoor")
    ziprecruiter_scraper = JSearchScraper(platform="ziprecruiter")

    with patch("src.adapters.scrapers.jsearch.requests.get",
               return_value=make_mock_response(_JSEARCH_RESPONSE)):
        indeed_results = await indeed_scraper.fetch_jobs("Python Developer", "Remote")
        glassdoor_results = await glassdoor_scraper.fetch_jobs("Python Developer", "Remote")
        ziprecruiter_results = await ziprecruiter_scraper.fetch_jobs("Python Developer", "Remote")

    assert indeed_results[0].platform == "indeed"
    assert glassdoor_results[0].platform == "glassdoor"
    assert ziprecruiter_results[0].platform == "ziprecruiter"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_http_error():
    """Error handling — returns empty list on HTTP error response."""
    scraper = JSearchScraper(platform="indeed")
    mock_response = make_mock_response({}, status=403)
    mock_response.raise_for_status = MagicMock(side_effect=requests.HTTPError("403"))

    with patch("src.adapters.scrapers.jsearch.requests.get", return_value=mock_response):
        results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_timeout():
    """Error handling — returns empty list on requests.Timeout."""
    scraper = JSearchScraper(platform="glassdoor")

    with patch("src.adapters.scrapers.jsearch.requests.get", side_effect=requests.Timeout):
        results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_when_no_results():
    """Edge case — returns empty list when API returns an empty data array."""
    scraper = JSearchScraper(platform="ziprecruiter")

    with patch("src.adapters.scrapers.jsearch.requests.get",
               return_value=make_mock_response({"data": []})):
        results = await scraper.fetch_jobs("Python Developer", "Remote")

    assert results == []
