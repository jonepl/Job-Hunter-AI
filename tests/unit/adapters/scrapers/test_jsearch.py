"""Unit tests for the JSearchScraper adapter."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.adapters.scrapers.jsearch import JSearchScraper
from src.core.domain.job import Job
from src.core.domain.work_type import WorkType

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


@pytest.mark.asyncio
async def test_remote_only_sets_remote_jobs_only_true():
    """Work type filter — remote only sets remote_jobs_only=true in params."""
    scraper = JSearchScraper(platform="indeed")
    captured_params = {}

    def capture_get(url, headers, params, timeout):
        captured_params.update(params)
        return make_mock_response(_JSEARCH_RESPONSE)

    with patch("src.adapters.scrapers.jsearch.requests.get", side_effect=capture_get):
        await scraper.fetch_jobs("Python Developer", "Remote", work_types=[WorkType.REMOTE])

    assert captured_params.get("remote_jobs_only") == "true"


@pytest.mark.asyncio
async def test_onsite_only_sets_remote_jobs_only_false():
    """Work type filter — onsite only sets remote_jobs_only=false in params."""
    scraper = JSearchScraper(platform="indeed")
    captured_params = {}

    def capture_get(url, headers, params, timeout):
        captured_params.update(params)
        return make_mock_response(_JSEARCH_RESPONSE)

    with patch("src.adapters.scrapers.jsearch.requests.get", side_effect=capture_get):
        await scraper.fetch_jobs("Python Developer", "New York", work_types=[WorkType.ONSITE])

    assert captured_params.get("remote_jobs_only") == "false"


@pytest.mark.asyncio
async def test_hybrid_omits_remote_jobs_only_with_warning(caplog):
    """Work type filter — hybrid omits remote_jobs_only and logs a WARNING."""
    import logging

    scraper = JSearchScraper(platform="indeed")
    captured_params = {}

    def capture_get(url, headers, params, timeout):
        captured_params.update(params)
        return make_mock_response(_JSEARCH_RESPONSE)

    with caplog.at_level(logging.WARNING, logger="src.adapters.scrapers.jsearch"):
        with patch("src.adapters.scrapers.jsearch.requests.get", side_effect=capture_get):
            await scraper.fetch_jobs("Python Developer", "New York", work_types=[WorkType.HYBRID])

    assert "remote_jobs_only" not in captured_params
    assert any("hybrid work type filter not natively supported" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_multiple_work_types_omits_remote_jobs_only(caplog):
    """Work type filter — multiple types omit remote_jobs_only and log INFO."""
    import logging

    scraper = JSearchScraper(platform="indeed")
    captured_params = {}

    def capture_get(url, headers, params, timeout):
        captured_params.update(params)
        return make_mock_response(_JSEARCH_RESPONSE)

    with caplog.at_level(logging.INFO, logger="src.adapters.scrapers.jsearch"):
        with patch("src.adapters.scrapers.jsearch.requests.get", side_effect=capture_get):
            await scraper.fetch_jobs(
                "Python Developer", "Remote",
                work_types=[WorkType.REMOTE, WorkType.HYBRID],
            )

    assert "remote_jobs_only" not in captured_params
    assert any("multiple work types" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_no_work_type_omits_remote_jobs_only():
    """Work type filter — None work_types omits remote_jobs_only entirely."""
    scraper = JSearchScraper(platform="indeed")
    captured_params = {}

    def capture_get(url, headers, params, timeout):
        captured_params.update(params)
        return make_mock_response(_JSEARCH_RESPONSE)

    with patch("src.adapters.scrapers.jsearch.requests.get", side_effect=capture_get):
        await scraper.fetch_jobs("Python Developer", "Remote", work_types=None)

    assert "remote_jobs_only" not in captured_params


@pytest.mark.asyncio
async def test_platform_label_in_log_messages(caplog):
    """Work type filter — platform label appears in work type log messages."""
    import logging

    scraper = JSearchScraper(platform="indeed")

    with caplog.at_level(logging.INFO, logger="src.adapters.scrapers.jsearch"):
        with patch("src.adapters.scrapers.jsearch.requests.get",
                   return_value=make_mock_response(_JSEARCH_RESPONSE)):
            await scraper.fetch_jobs("Python Developer", "Remote", work_types=[WorkType.REMOTE])

    assert any("indeed" in r.message for r in caplog.records)
