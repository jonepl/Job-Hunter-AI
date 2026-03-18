"""Unit tests for JobSearchService orchestration logic."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume
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


def make_match_result(job: Job, score: int) -> MatchResult:
    """Return a MatchResult with the given score."""
    return MatchResult(
        job=job,
        score=score,
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
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_returns_ranked_results_above_threshold():
    """Happy path — run() returns results sorted by score descending."""
    jobs = [make_job("Job A"), make_job("Job B"), make_job("Job C")]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=[70, 90, 80],
    )

    results = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert len(results) == 3
    assert results[0].score == 90
    assert results[1].score == 80
    assert results[2].score == 70


@pytest.mark.asyncio
async def test_run_filters_results_below_threshold():
    """Filtering — jobs scoring below threshold are excluded from results."""
    jobs = [make_job("High"), make_job("Low")]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=[85, 50],
    )

    results = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert len(results) == 1
    assert results[0].score == 85


@pytest.mark.asyncio
async def test_run_caps_results_at_top_10():
    """Ranking — run() returns at most 10 results even when more qualify."""
    jobs = [make_job(f"Job {i}") for i in range(15)]
    scores = list(range(71, 86))  # 15 scores all above 70
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=scores,
    )

    results = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert len(results) == 10
    assert results[0].score == max(scores)


@pytest.mark.asyncio
async def test_run_handles_scraper_exception_gracefully():
    """Error handling — a failing scraper is logged and skipped; pipeline continues."""
    good_jobs = [make_job("Good Job")]
    service, _, _, output = make_service(
        scraper_jobs=[good_jobs, []],
        eval_scores=[80],
        scraper_exceptions=[None, RuntimeError("Scraper failed")],
    )

    results = await service.run(query="Python Developer", location="Remote", threshold=70)

    # Pipeline continues — good scraper result is returned
    assert len(results) == 1
    assert results[0].score == 80
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
async def test_run_returns_empty_list_when_no_jobs_meet_threshold():
    """Edge case — returns empty list when all jobs score below threshold."""
    service, _, _, _ = make_service(
        scraper_jobs=[[make_job()]],
        eval_scores=[30],
    )

    results = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert results == []


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

    scrapers[0].fetch_jobs.assert_called_once_with("Python Developer", "Remote")
    scrapers[1].fetch_jobs.assert_called_once_with("Python Developer", "Remote")
