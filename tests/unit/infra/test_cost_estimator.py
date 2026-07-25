"""Unit tests for the CostEstimator infra module."""

from unittest.mock import patch

from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.infra.cost_estimator import estimate_run_cost


def _make_profile(scrapers: list[ScraperName]) -> SearchProfile:
    """Return a minimal SearchProfile with the given active scrapers."""
    return SearchProfile(
        profile_id=1,
        query="Software Engineer",
        location="Remote",
        active_scrapers=scrapers,
        score_threshold=75,
    )


@patch.dict("os.environ", {"JSEARCH_MAX_PAGES": "2"})
def test_estimate_max_jobs_all_four_scrapers():
    """All four scrapers: 3 JSearch * 2 pages * 10 + 1 LinkedIn * 25 = 85 jobs."""
    profile = _make_profile(
        [
            ScraperName.LINKEDIN,
            ScraperName.INDEED,
            ScraperName.GLASSDOOR,
            ScraperName.ZIPRECRUITER,
        ]
    )
    estimate = estimate_run_cost(
        profile=profile,
        provider="openai",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
    )
    assert estimate.max_jobs == 85


@patch.dict("os.environ", {"JSEARCH_MAX_PAGES": "2"})
def test_estimate_max_jobs_linkedin_only():
    """LinkedIn only: 0 JSearch + 1 LinkedIn * 25 = 25 jobs."""
    profile = _make_profile([ScraperName.LINKEDIN])
    estimate = estimate_run_cost(
        profile=profile,
        provider="openai",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
    )
    assert estimate.max_jobs == 25


@patch.dict("os.environ", {"JSEARCH_MAX_PAGES": "2"})
def test_estimate_max_jobs_jsearch_only():
    """Indeed, Glassdoor, ZipRecruiter only: 3 * 2 * 10 = 60 jobs."""
    profile = _make_profile(
        [
            ScraperName.INDEED,
            ScraperName.GLASSDOOR,
            ScraperName.ZIPRECRUITER,
        ]
    )
    estimate = estimate_run_cost(
        profile=profile,
        provider="openai",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
    )
    assert estimate.max_jobs == 60


@patch.dict("os.environ", {"JSEARCH_MAX_PAGES": "2"})
def test_estimate_cost_range_is_ordered():
    """est_min_cost_usd is always less than or equal to est_max_cost_usd."""
    profile = _make_profile([ScraperName.INDEED, ScraperName.LINKEDIN])
    estimate = estimate_run_cost(
        profile=profile,
        provider="openai",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
    )
    assert estimate.est_min_cost_usd <= estimate.est_max_cost_usd


@patch.dict("os.environ", {"JSEARCH_MAX_PAGES": "2"})
def test_estimate_uses_configured_rates():
    """Higher configured rates produce higher cost estimates."""
    profile = _make_profile([ScraperName.INDEED])

    estimate_low = estimate_run_cost(
        profile=profile,
        provider="openai",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
    )
    estimate_high = estimate_run_cost(
        profile=profile,
        provider="openai",
        input_cost_per_1m=5.00,
        output_cost_per_1m=20.00,
    )

    assert estimate_high.est_min_cost_usd > estimate_low.est_min_cost_usd
    assert estimate_high.est_max_cost_usd > estimate_low.est_max_cost_usd
    assert estimate_high.input_cost_per_1m == 5.00
    assert estimate_high.output_cost_per_1m == 20.00
