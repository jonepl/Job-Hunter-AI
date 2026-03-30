"""Unit tests for JobSearchService orchestration logic."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.domain.date_posted import DatePosted
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.resume import Resume
from src.core.domain.run_report import RunReport
from src.core.domain.scraper_name import ScraperName
from src.core.services.job_search_service import JobSearchService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_job(title: str = "Engineer", platform: str = "linkedin") -> Job:
    """Return a minimal valid Job for use in tests."""
    return Job(
        title=title,
        company="Acme",
        location="Remote",
        url="https://example.com/jobs/1",
        description="A job description.",
        platform=platform,
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )


def _zero_breakdown() -> ScoreBreakdown:
    """Return a zero-value ScoreBreakdown for service test fixtures."""
    def _z(max_val: int) -> ScoreCategory:
        return ScoreCategory(max=max_val, earned=0, reasoning="n/a")

    return ScoreBreakdown(
        role_alignment=_z(20),
        technical_stack_match=_z(15),
        system_design_architecture=_z(15),
        impact_and_metrics=_z(15),
        domain_industry_experience=_z(10),
        problem_space_relevance=_z(10),
        ownership_and_leadership=_z(10),
        resume_signal_quality=_z(3),
        career_trajectory=_z(2),
    )


def make_match_result(job: Job, score: int) -> MatchResult:
    """Return a MatchResult with the given score."""
    return MatchResult(
        job=job,
        score=score,
        seniority_level="Mid-Level",
        years_experience_detected=None,
        hire_recommendation="Yes",
        score_breakdown=_zero_breakdown(),
        matched_skills=["Python"],
        missing_skills=[],
        summary="Test result.",
    )


def make_service(
    scraper_jobs: list[list[Job]] | None = None,
    eval_scores: list[int] | None = None,
    scraper_exceptions: list[Exception | None] | None = None,
) -> tuple[JobSearchService, MagicMock, MagicMock, MagicMock]:
    """Build a JobSearchService with fully mocked dependencies.

    Args:
        scraper_jobs: List of job lists returned by each scraper.
        eval_scores: Scores returned by the evaluator, one per job in order.
        scraper_exceptions: Per-scraper exceptions (None means success).

    Returns:
        Tuple of (service, scraper_mock, evaluator_mock, output_mock).
    """
    scraper_jobs = scraper_jobs or [[make_job()]]
    eval_scores = eval_scores or [80]

    scrapers = []
    for i, jobs in enumerate(scraper_jobs):
        mock = MagicMock()
        exc = (scraper_exceptions or [])[i] if scraper_exceptions and i < len(scraper_exceptions) else None
        if exc:
            mock.fetch_jobs = AsyncMock(side_effect=exc)
        else:
            mock.fetch_jobs = AsyncMock(return_value=jobs)
        scrapers.append(mock)

    jobs_flat = [job for jobs in scraper_jobs for job in jobs]
    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(
        side_effect=[make_match_result(job, score) for job, score in zip(jobs_flat, eval_scores)]
    )

    output = MagicMock()
    output.deliver = AsyncMock()

    sample_resume = Resume(
        raw_text="Experienced Python developer.",
        parsed_at=datetime(2026, 3, 17, 9, 0, 0),
    )

    service = JobSearchService(
        scrapers=scrapers,
        evaluator=evaluator,
        outputs=[output],
        resume_path="docs/resume/resume.pdf",
    )

    # Patch _parse_resume so no real file I/O occurs in unit tests
    service._parse_resume = MagicMock(return_value=sample_resume)

    return service, scrapers, evaluator, output


# ---------------------------------------------------------------------------
# Existing tests — updated for RunReport return type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_returns_ranked_results_above_threshold():
    """Happy path — run() returns qualifying results sorted by score descending."""
    jobs = [make_job("Job A"), make_job("Job B"), make_job("Job C")]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=[70, 90, 80],
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert len(report.qualifying_results) == 3
    assert report.qualifying_results[0].score == 90
    assert report.qualifying_results[1].score == 80
    assert report.qualifying_results[2].score == 70


@pytest.mark.asyncio
async def test_run_filters_results_below_threshold():
    """Filtering — jobs scoring below threshold are excluded from qualifying results."""
    jobs = [make_job("High"), make_job("Low")]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=[85, 50],
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert len(report.qualifying_results) == 1
    assert report.qualifying_results[0].score == 85


@pytest.mark.asyncio
async def test_run_handles_scraper_exception_gracefully():
    """Error handling — a failing scraper is logged and skipped; pipeline continues."""
    good_jobs = [make_job("Good Job")]
    service, _, _, output = make_service(
        scraper_jobs=[good_jobs, []],
        eval_scores=[80],
        scraper_exceptions=[None, RuntimeError("Scraper failed")],
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70)

    # Pipeline continues — good scraper result is returned
    assert len(report.qualifying_results) == 1
    assert report.qualifying_results[0].score == 80
    # Output was still called
    output.deliver.assert_called_once()


@pytest.mark.asyncio
async def test_run_calls_all_output_adapters():
    """Output — run() calls deliver() on every registered output adapter."""
    output_a = MagicMock()
    output_a.deliver = AsyncMock()
    output_b = MagicMock()
    output_b.deliver = AsyncMock()

    job = make_job()
    scraper = MagicMock()
    scraper.fetch_jobs = AsyncMock(return_value=[job])
    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(return_value=make_match_result(job, 80))

    service = JobSearchService(
        scrapers=[scraper],
        evaluator=evaluator,
        outputs=[output_a, output_b],
    )
    service._parse_resume = MagicMock(
        return_value=Resume(
            raw_text="resume text",
            parsed_at=datetime(2026, 3, 17, 9, 0, 0),
        )
    )

    await service.run(query="Python Developer", location="Remote", threshold=70)

    output_a.deliver.assert_called_once()
    output_b.deliver.assert_called_once()


@pytest.mark.asyncio
async def test_run_returns_empty_qualifying_when_no_jobs_meet_threshold():
    """Edge case — qualifying_results is empty when all jobs score below threshold."""
    service, _, _, _ = make_service(
        scraper_jobs=[[make_job()]],
        eval_scores=[30],
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert report.qualifying_results == []
    assert report.has_qualifying_results is False


@pytest.mark.asyncio
async def test_run_scrapes_all_platforms_concurrently():
    """Concurrency — fetch_jobs is called on every registered scraper."""
    jobs_a = [make_job("Job A")]
    jobs_b = [make_job("Job B")]
    service, scrapers, _, _ = make_service(
        scraper_jobs=[jobs_a, jobs_b],
        eval_scores=[80, 75],
    )

    await service.run(query="Python Developer", location="Remote", threshold=70)

    scrapers[0].fetch_jobs.assert_called_once_with("Python Developer", "Remote", work_types=None, date_posted=None)
    scrapers[1].fetch_jobs.assert_called_once_with("Python Developer", "Remote", work_types=None, date_posted=None)


# ---------------------------------------------------------------------------
# New tests — RunReport return type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_run_report_not_list():
    """run() returns a RunReport instance, not a list."""
    service, _, _, _ = make_service(eval_scores=[80])
    result = await service.run(query="Python Developer", location="Remote", threshold=70)
    assert isinstance(result, RunReport)


@pytest.mark.asyncio
async def test_near_misses_populated_when_zero_qualifying():
    """near_miss_results is populated when all jobs score below threshold."""
    jobs = [make_job(f"Job {i}") for i in range(3)]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=[60, 55, 50],
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert report.qualifying_results == []
    assert len(report.near_miss_results) > 0
    assert all(r.score < 70 for r in report.near_miss_results)


@pytest.mark.asyncio
async def test_near_misses_empty_when_qualifying_exist():
    """near_miss_results is empty when qualifying results exist."""
    service, _, _, _ = make_service(
        scraper_jobs=[[make_job()]],
        eval_scores=[80],
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert report.has_qualifying_results is True
    assert report.near_miss_results == []


@pytest.mark.asyncio
async def test_near_misses_capped_at_five():
    """near_miss_results contains at most 5 results even when more jobs fail threshold."""
    jobs = [make_job(f"Job {i}") for i in range(10)]
    scores = [60, 58, 56, 54, 52, 50, 48, 46, 44, 42]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=scores,
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert len(report.near_miss_results) == 5


@pytest.mark.asyncio
async def test_zero_results_warning_logged(caplog):
    """WARNING log is emitted when zero jobs pass the threshold."""
    import logging
    service, _, _, _ = make_service(
        scraper_jobs=[[make_job()]],
        eval_scores=[30],
    )

    with caplog.at_level(logging.WARNING):
        await service.run(query="Python Developer", location="Remote", threshold=70)

    assert any("0 qualifying results" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_top_results_caps_output():
    """qualifying_results is capped at top_results when set and more qualify."""
    jobs = [make_job(f"Job {i}") for i in range(8)]
    scores = [90, 88, 86, 84, 82, 80, 78, 76]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=scores,
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70, top_results=5)

    assert len(report.qualifying_results) == 5
    assert report.qualifying_results[0].score == 90
    assert report.qualifying_results[4].score == 82


@pytest.mark.asyncio
async def test_top_results_returns_all_when_under_cap():
    """All qualifying results returned when count is below top_results cap."""
    jobs = [make_job(f"Job {i}") for i in range(3)]
    scores = [80, 75, 72]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=scores,
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70, top_results=5)

    assert len(report.qualifying_results) == 3


@pytest.mark.asyncio
async def test_top_results_applied_after_score_filter():
    """top_results cap is applied only to jobs that passed the threshold."""
    jobs = [make_job(f"Job {i}") for i in range(10)]
    # 4 above threshold (90, 85, 80, 75), 6 below (65, 60, 55, 50, 45, 40)
    scores = [90, 85, 80, 75, 65, 60, 55, 50, 45, 40]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=scores,
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70, top_results=3)

    assert len(report.qualifying_results) == 3
    assert all(r.score >= 70 for r in report.qualifying_results)


@pytest.mark.asyncio
async def test_top_results_not_set_returns_all_qualifying():
    """All qualifying results returned when top_results is None."""
    jobs = [make_job(f"Job {i}") for i in range(15)]
    scores = [71 + i for i in range(15)]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=scores,
    )

    report = await service.run(
        query="Python Developer", location="Remote", threshold=70, top_results=None
    )

    assert len(report.qualifying_results) == 15


@pytest.mark.asyncio
async def test_top_results_none_logged_correctly(caplog):
    """INFO log contains 'not set' when top_results is None."""
    import logging
    service, _, _, _ = make_service(eval_scores=[80])

    with caplog.at_level(logging.INFO):
        await service.run(
            query="Python Developer", location="Remote", threshold=70, top_results=None
        )

    assert any("not set" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# New tests — date_posted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_date_posted_passed_to_all_scrapers():
    """date_posted=WEEK is forwarded to every scraper via fetch_jobs."""
    jobs_a = [make_job("Job A")]
    jobs_b = [make_job("Job B")]
    service, scrapers, _, _ = make_service(
        scraper_jobs=[jobs_a, jobs_b],
        eval_scores=[80, 75],
    )

    await service.run(
        query="Python Developer", location="Remote", threshold=70, date_posted=DatePosted.WEEK
    )

    scrapers[0].fetch_jobs.assert_called_once_with(
        "Python Developer", "Remote", work_types=None, date_posted=DatePosted.WEEK
    )
    scrapers[1].fetch_jobs.assert_called_once_with(
        "Python Developer", "Remote", work_types=None, date_posted=DatePosted.WEEK
    )


@pytest.mark.asyncio
async def test_no_date_posted_passes_none_to_scrapers():
    """date_posted=None is forwarded to every scraper via fetch_jobs."""
    jobs_a = [make_job("Job A")]
    jobs_b = [make_job("Job B")]
    service, scrapers, _, _ = make_service(
        scraper_jobs=[jobs_a, jobs_b],
        eval_scores=[80, 75],
    )

    await service.run(
        query="Python Developer", location="Remote", threshold=70, date_posted=None
    )

    scrapers[0].fetch_jobs.assert_called_once_with(
        "Python Developer", "Remote", work_types=None, date_posted=None
    )
    scrapers[1].fetch_jobs.assert_called_once_with(
        "Python Developer", "Remote", work_types=None, date_posted=None
    )


@pytest.mark.asyncio
async def test_date_posted_in_run_report():
    """RunReport.date_posted matches the value passed to run()."""
    service, _, _, _ = make_service(eval_scores=[80])

    report = await service.run(
        query="Python Developer", location="Remote", threshold=70, date_posted=DatePosted.DAYS3
    )

    assert report.date_posted == DatePosted.DAYS3


@pytest.mark.asyncio
async def test_date_posted_logged_at_pipeline_start(caplog):
    """INFO log contains the date_posted value when date_posted is set."""
    import logging
    service, _, _, _ = make_service(eval_scores=[80])

    with caplog.at_level(logging.INFO):
        await service.run(
            query="Python Developer", location="Remote", threshold=70, date_posted=DatePosted.WEEK
        )

    assert any("week" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# New tests — active_scrapers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_only_active_scrapers_called():
    """Only the scrapers passed to the service are called — no extras."""
    jobs_a = [make_job("Job A")]
    jobs_b = [make_job("Job B")]
    service, scrapers, _, _ = make_service(
        scraper_jobs=[jobs_a, jobs_b],
        eval_scores=[80, 75],
    )

    await service.run(query="Python Developer", location="Remote", threshold=70)

    # Both registered scrapers are called exactly once
    scrapers[0].fetch_jobs.assert_called_once()
    scrapers[1].fetch_jobs.assert_called_once()
    # Confirm the service has exactly the two scrapers we passed
    assert len(service._scrapers) == 2


@pytest.mark.asyncio
async def test_active_scrapers_in_run_report():
    """RunReport.active_scrapers matches the list passed to run()."""
    service, _, _, _ = make_service(eval_scores=[80])
    active = [ScraperName.LINKEDIN, ScraperName.INDEED]

    report = await service.run(
        query="Python Developer",
        location="Remote",
        threshold=70,
        active_scrapers=active,
    )

    assert report.active_scrapers == active
