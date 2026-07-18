"""Unit tests for JobSearchService orchestration logic."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.domain.date_posted import DatePosted
from src.core.domain.fingerprint import compute_fingerprint
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.resume import Resume
from src.core.domain.run_report import RunReport
from src.core.domain.scraper_name import ScraperName
from src.core.exceptions import ModelNotFoundError
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
        side_effect=[(make_match_result(job, score), 100, 50) for job, score in zip(jobs_flat, eval_scores)]
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
async def test_run_propagates_model_not_found_error():
    """A ModelNotFoundError from the evaluator aborts the run (no zero-results report)."""
    service, _, evaluator, output = make_service(scraper_jobs=[[make_job()]])
    evaluator.evaluate = AsyncMock(side_effect=ModelNotFoundError("bad model"))

    with pytest.raises(ModelNotFoundError):
        await service.run(query="Python Developer", location="Remote", threshold=70)

    # The run must not deliver a misleading empty report on a config error.
    output.deliver.assert_not_called()


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
    evaluator.evaluate = AsyncMock(return_value=(make_match_result(job, 80), 100, 50))

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
    """near_miss_results caps at 5, and only counts scores inside the band (ADR-033).

    Threshold 70, default band 15 → near-miss window [55, 70). Six scores fall in
    the band (capped to 5); scores below 55 are 'below', never near-miss.
    """
    jobs = [make_job(f"Job {i}") for i in range(8)]
    scores = [69, 68, 67, 66, 65, 64, 50, 40]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=scores,
    )

    report = await service.run(query="Python Developer", location="Remote", threshold=70)

    assert len(report.near_miss_results) == 5
    assert all(r.score >= 55 for r in report.near_miss_results)


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


# ---------------------------------------------------------------------------
# New tests — cost_tracker integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cost_tracker_called_per_evaluation():
    """cost_tracker.record() is called once per evaluated job."""
    from unittest.mock import MagicMock as MM

    jobs = [make_job("Job A"), make_job("Job B"), make_job("Job C")]
    service, _, _, _ = make_service(
        scraper_jobs=[jobs],
        eval_scores=[80, 75, 72],
    )

    cost_tracker = MM()
    cost_tracker.record = MM(return_value=None)
    cost_tracker.build_run_cost = MM(return_value=None)

    await service.run(
        query="Python Developer",
        location="Remote",
        threshold=70,
        cost_tracker=cost_tracker,
    )

    assert cost_tracker.record.call_count == 3


@pytest.mark.asyncio
async def test_cost_tracker_not_called_when_none():
    """Passing cost_tracker=None does not raise AttributeError."""
    service, _, _, _ = make_service(eval_scores=[80])

    # Should complete without error
    report = await service.run(
        query="Python Developer",
        location="Remote",
        threshold=70,
        cost_tracker=None,
    )

    assert isinstance(report, RunReport)


@pytest.mark.asyncio
async def test_run_report_includes_run_cost():
    """RunReport.run_cost is populated when cost_tracker returns a RunCost."""
    from unittest.mock import MagicMock as MM
    from src.core.domain.run_cost import RunCost, EvaluationCost

    jobs = [make_job()]
    service, _, _, _ = make_service(scraper_jobs=[jobs], eval_scores=[80])

    mock_run_cost = RunCost(
        evaluations=[EvaluationCost(
            job_title="Engineer", company="Acme",
            input_tokens=100, output_tokens=50, cost_usd=0.001,
        )],
        total_input_tokens=100,
        total_output_tokens=50,
        total_cost_usd=0.001,
        provider="openai",
        jobs_evaluated=1,
    )

    cost_tracker = MM()
    cost_tracker.record = MM(return_value=None)
    cost_tracker.build_run_cost = MM(return_value=mock_run_cost)

    report = await service.run(
        query="Python Developer",
        location="Remote",
        threshold=70,
        cost_tracker=cost_tracker,
    )

    assert report.run_cost is not None
    assert report.run_cost.jobs_evaluated == 1


# ---------------------------------------------------------------------------
# Rate limiting tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluation_delay_applied():
    """asyncio.sleep is called with EVALUATION_DELAY_SECONDS after each evaluation."""
    jobs = [make_job("Job A"), make_job("Job B")]
    service, _, _, _ = make_service(scraper_jobs=[jobs], eval_scores=[80, 75])

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with patch.dict("os.environ", {"EVALUATION_DELAY_SECONDS": "2.5"}):
            await service.run(
                query="Python Developer",
                location="Remote",
                threshold=70,
            )

    assert mock_sleep.call_count == len(jobs)
    mock_sleep.assert_called_with(2.5)


@pytest.mark.asyncio
async def test_max_concurrent_default_is_two():
    """MAX_CONCURRENT_EVALUATIONS defaults to 2 when env var is not set."""
    jobs = [make_job()]
    service, _, _, _ = make_service(scraper_jobs=[jobs], eval_scores=[80])

    with patch("asyncio.Semaphore", wraps=asyncio.Semaphore) as mock_semaphore:
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("MAX_CONCURRENT_EVALUATIONS", None)
            await service.run(
                query="Python Developer",
                location="Remote",
                threshold=70,
            )

    mock_semaphore.assert_called_once_with(2)


@pytest.mark.asyncio
async def test_max_concurrent_loaded_from_env():
    """MAX_CONCURRENT_EVALUATIONS is read from env when set."""
    jobs = [make_job()]
    service, _, _, _ = make_service(scraper_jobs=[jobs], eval_scores=[80])

    with patch("asyncio.Semaphore", wraps=asyncio.Semaphore) as mock_semaphore:
        with patch.dict("os.environ", {"MAX_CONCURRENT_EVALUATIONS": "5"}):
            await service.run(
                query="Python Developer",
                location="Remote",
                threshold=70,
            )

    mock_semaphore.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# Pre-filter (JobEnrichmentPort) tests — A2
# ---------------------------------------------------------------------------

from src.core.domain.enrichment_result import EnrichmentResult  # noqa: E402


@pytest.fixture
def no_sleep():
    """Patch asyncio.sleep so the eval/pre-filter throttle delays don't slow tests."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        yield


def _enrich_service(jobs, flags, scores, mode, errored=None, circuit_broken=False):
    """Build a JobSearchService wired with a mocked pre-filter.

    Args:
        jobs: The jobs the single scraper returns.
        flags: Parallel list of should_skip booleans, one per job.
        scores: Mapping of job title -> evaluator score.
        mode: 'shadow' or 'enforce'.
        errored: Optional parallel list of errored booleans (defaults all False).
        circuit_broken: Value of the enrichment adapter's circuit_broken property.

    Returns:
        Tuple of (service, evaluator_mock, enrichment_mock, output_mock).
    """
    errored = errored or [False] * len(flags)
    scraper = MagicMock()
    scraper.fetch_jobs = AsyncMock(return_value=jobs)

    async def _eval(resume, job, work_types=None):
        return make_match_result(job, scores[job.title]), 100, 50

    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(side_effect=_eval)

    enrichment = MagicMock()
    enrichment.enrich = AsyncMock(
        side_effect=[
            EnrichmentResult(should_skip=f, reason="reason", errored=e)
            for f, e in zip(flags, errored)
        ]
    )
    enrichment.circuit_broken = circuit_broken

    output = MagicMock()
    output.deliver = AsyncMock()

    resume = Resume(raw_text="Experienced dev.", parsed_at=datetime(2026, 3, 17, 9, 0, 0))
    service = JobSearchService(
        scrapers=[scraper],
        evaluator=evaluator,
        outputs=[output],
        enrichment=enrichment,
        enrichment_mode=mode,
    )
    service._parse_resume = MagicMock(return_value=resume)
    return service, evaluator, enrichment, output


@pytest.mark.asyncio
async def test_no_enrichment_summary_when_port_absent(no_sleep):
    """Without a pre-filter the report carries no enrichment summary."""
    service, _, _, _ = make_service(scraper_jobs=[[make_job()]], eval_scores=[80])

    report = await service.run(query="Q", location="Remote", threshold=70)

    assert report.enrichment_summary is None


@pytest.mark.asyncio
async def test_shadow_mode_evaluates_all_and_measures_false_skips(no_sleep):
    """Shadow mode evaluates every job and counts flagged jobs that still qualify."""
    jobs = [make_job("A"), make_job("B"), make_job("C")]
    service, evaluator, _, _ = _enrich_service(
        jobs,
        flags=[True, False, False],
        scores={"A": 85, "B": 60, "C": 90},
        mode="shadow",
    )

    report = await service.run(query="Q", location="Remote", threshold=70)

    # Shadow never skips: all three evaluated, A still qualifies.
    assert evaluator.evaluate.await_count == 3
    assert report.total_evaluated == 3
    assert {r.job.title for r in report.qualifying_results} == {"A", "C"}

    summary = report.enrichment_summary
    assert summary is not None
    assert summary.mode == "shadow"
    assert summary.flagged_count == 1
    assert summary.false_skips == 1  # A was flagged but scored 85 >= 70
    assert summary.false_skip_rate == 1.0


@pytest.mark.asyncio
async def test_shadow_mode_zero_false_skips_when_flagged_below_threshold(no_sleep):
    """A flagged job that scores below threshold is a correct skip, not a false one."""
    jobs = [make_job("A")]
    service, _, _, _ = _enrich_service(
        jobs, flags=[True], scores={"A": 50}, mode="shadow"
    )

    report = await service.run(query="Q", location="Remote", threshold=70)

    summary = report.enrichment_summary
    assert summary.false_skips == 0
    assert summary.false_skip_rate == 0.0


@pytest.mark.asyncio
async def test_enforce_mode_withholds_flagged_jobs_from_evaluation(no_sleep):
    """Enforce mode skips flagged jobs entirely — evaluator never sees them."""
    jobs = [make_job("A"), make_job("B"), make_job("C")]
    service, evaluator, _, _ = _enrich_service(
        jobs,
        flags=[True, False, False],
        scores={"B": 60, "C": 90},
        mode="enforce",
    )

    report = await service.run(query="Q", location="Remote", threshold=70)

    # Only the two non-flagged jobs are evaluated.
    assert evaluator.evaluate.await_count == 2
    assert report.total_evaluated == 2
    assert "A" not in {r.job.title for r in report.qualifying_results}

    summary = report.enrichment_summary
    assert summary.mode == "enforce"
    assert summary.flagged_count == 1
    # False-skips are unmeasurable in enforce mode.
    assert summary.false_skips is None
    assert summary.false_skip_rate is None


@pytest.mark.asyncio
async def test_estimated_savings_none_without_cost_tracker(no_sleep):
    """Estimated savings is None when cost tracking is disabled."""
    jobs = [make_job("A"), make_job("B")]
    service, _, _, _ = _enrich_service(
        jobs, flags=[True, False], scores={"A": 40, "B": 80}, mode="shadow"
    )

    report = await service.run(query="Q", location="Remote", threshold=70)

    assert report.enrichment_summary.estimated_savings_usd is None


@pytest.mark.asyncio
async def test_error_count_surfaced_when_pre_filter_fails(no_sleep):
    """Fail-open verdicts are counted so a degraded pre-filter is visible."""
    jobs = [make_job("A"), make_job("B"), make_job("C")]
    # All three failed open (errored) — none were genuinely assessed.
    service, evaluator, _, _ = _enrich_service(
        jobs,
        flags=[False, False, False],
        errored=[True, True, True],
        scores={"A": 80, "B": 60, "C": 90},
        mode="shadow",
        circuit_broken=True,
    )

    report = await service.run(query="Q", location="Remote", threshold=70)

    # Fail-open means every job still went to evaluation.
    assert evaluator.evaluate.await_count == 3
    summary = report.enrichment_summary
    assert summary.error_count == 3
    assert summary.flagged_count == 0
    assert summary.circuit_broken is True
    # A fully-errored run is not graduation-ready even with 0 false-skips.
    assert summary.graduation_ready is False


@pytest.mark.asyncio
async def test_enrichment_throttle_reads_env(no_sleep):
    """The pre-filter stage sizes its semaphore from ENRICHMENT_MAX_CONCURRENT."""
    jobs = [make_job("A")]
    service, _, _, _ = _enrich_service(
        jobs, flags=[False], scores={"A": 80}, mode="shadow"
    )

    with patch("asyncio.Semaphore", wraps=asyncio.Semaphore) as mock_semaphore:
        with patch.dict("os.environ", {"ENRICHMENT_MAX_CONCURRENT": "4"}):
            await service.run(query="Q", location="Remote", threshold=70)

    sizes = [c.args[0] for c in mock_semaphore.call_args_list if c.args]
    assert 4 in sizes


# ---------------------------------------------------------------------------
# B1 — dedup, reuse, sightings, near-misses (JobRepositoryPort)
# ---------------------------------------------------------------------------

def _same_job(platform: str, url: str = "https://example.com/jobs/1") -> Job:
    """Return a job with a fixed identity but overridable platform/url."""
    return Job(
        title="Senior Software Engineer",
        company="Acme",
        location="Remote",
        url=url,
        description="A job description.",
        platform=platform,
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )


def _service_with_repo(scraper_jobs, score_by_title=None, repository=None):
    """Build a service wired to a real in-memory repository and a callable evaluator.

    The evaluator is a callable AsyncMock so it can be invoked any number of
    times across runs without pre-sizing a side-effect list.
    """
    from src.adapters.repository.sqlite_repository import SQLiteJobRepository

    repository = repository or SQLiteJobRepository(db_path=":memory:")
    score_by_title = score_by_title or {}

    scraper_mocks = []
    for jobs in scraper_jobs:
        mock = MagicMock()
        mock.fetch_jobs = AsyncMock(return_value=jobs)
        scraper_mocks.append(mock)

    async def _evaluate(resume, job, work_types=None):
        return make_match_result(job, score_by_title.get(job.title, 80)), 100, 50

    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(side_effect=_evaluate)

    output = MagicMock()
    output.deliver = AsyncMock()

    service = JobSearchService(
        scrapers=scraper_mocks,
        evaluator=evaluator,
        outputs=[output],
        repository=repository,
    )
    service._parse_resume = MagicMock(
        return_value=Resume(raw_text="resume", parsed_at=datetime(2026, 3, 17))
    )
    return service, evaluator, repository


@pytest.mark.asyncio
async def test_seen_job_skips_reevaluation_on_second_run():
    """A previously stored job reuses its score and is not re-evaluated."""
    from src.adapters.repository.sqlite_repository import SQLiteJobRepository

    repo = SQLiteJobRepository(db_path=":memory:")
    service, evaluator, _ = _service_with_repo(
        [[_same_job("linkedin")]], score_by_title={"Senior Software Engineer": 88}, repository=repo
    )

    report1 = await service.run(query="Q", location="Remote", threshold=70)
    assert evaluator.evaluate.call_count == 1
    assert report1.reused_count == 0
    assert len(report1.qualifying_results) == 1

    report2 = await service.run(query="Q", location="Remote", threshold=70)
    # Not re-evaluated — the stored score is reused.
    assert evaluator.evaluate.call_count == 1
    assert report2.reused_count == 1
    assert report2.qualifying_results[0].score == 88


@pytest.mark.asyncio
async def test_same_job_across_platforms_evaluated_once_with_seen_on():
    """The same posting on two platforms in one run is evaluated once (seen on both)."""
    service, evaluator, _ = _service_with_repo(
        [[_same_job("linkedin")], [_same_job("indeed", url="https://indeed.com/1")]]
    )

    report = await service.run(query="Q", location="Remote", threshold=70)

    assert evaluator.evaluate.call_count == 1
    assert len(report.qualifying_results) == 1
    assert report.qualifying_results[0].seen_on == ["indeed", "linkedin"]


@pytest.mark.asyncio
async def test_near_miss_is_logged_not_merged(caplog):
    """A same-company/title job at a new location is logged and re-evaluated (not merged)."""
    import logging

    from src.adapters.repository.sqlite_repository import SQLiteJobRepository

    repo = SQLiteJobRepository(db_path=":memory:")

    ny_job = _same_job("linkedin")
    ny_job = ny_job.model_copy(update={"location": "New York, NY"})
    tx_job = _same_job("linkedin", url="https://example.com/jobs/2")
    tx_job = tx_job.model_copy(update={"location": "Austin, TX"})

    service_ny, evaluator, _ = _service_with_repo([[ny_job]], repository=repo)
    await service_ny.run(query="Q", location="New York, NY", threshold=70)

    service_tx, evaluator2, _ = _service_with_repo([[tx_job]], repository=repo)
    with caplog.at_level(logging.INFO, logger="src.core.services.job_search_service"):
        report = await service_tx.run(query="Q", location="Austin, TX", threshold=70)

    # The TX job is a distinct fingerprint — evaluated fresh, not reused.
    assert report.reused_count == 0
    assert evaluator2.evaluate.call_count == 1
    assert any("Near-miss" in rec.message for rec in caplog.records)
    # Both distinct jobs persisted.
    assert repo.find_by_fingerprint(
        compute_fingerprint("Acme", "Senior Software Engineer", "New York, NY").key
    ) is not None
    assert repo.find_by_fingerprint(
        compute_fingerprint("Acme", "Senior Software Engineer", "Austin, TX").key
    ) is not None


@pytest.mark.asyncio
async def test_new_evaluation_is_persisted():
    """A newly evaluated job is written to the repository with its threshold."""
    from src.adapters.repository.sqlite_repository import SQLiteJobRepository

    repo = SQLiteJobRepository(db_path=":memory:")
    service, _, _ = _service_with_repo([[_same_job("linkedin")]], repository=repo)

    await service.run(query="Q", location="Remote", threshold=72)

    stored = repo.find_by_fingerprint(
        compute_fingerprint("Acme", "Senior Software Engineer", "Remote").key
    )
    assert stored is not None
    assert stored.threshold == 72
    assert stored.near_miss_floor == 72 - 15


@pytest.mark.asyncio
async def test_human_acted_job_is_suppressed_but_still_sighted():
    """A re-scraped job with a human-set status is withheld from the report.

    The sighting is still recorded (the store stays current for the later
    TRACKED view) and the human status is never clobbered (ADR-025).
    """
    from src.adapters.repository.sqlite_repository import SQLiteJobRepository
    from src.core.domain.job_status import JobStatus

    repo = SQLiteJobRepository(db_path=":memory:")
    service, evaluator, _ = _service_with_repo(
        [[_same_job("linkedin")]],
        score_by_title={"Senior Software Engineer": 88},
        repository=repo,
    )

    # First run persists + evaluates the job.
    report1 = await service.run(query="Q", location="Remote", threshold=70)
    assert len(report1.qualifying_results) == 1
    fp = compute_fingerprint("Acme", "Senior Software Engineer", "Remote")
    stored = repo.find_by_fingerprint(fp.key)

    # A human marks it applied.
    repo.set_status(stored.id, JobStatus.APPLIED)

    # Re-scrape on a new platform — suppressed from the report, sighting recorded.
    service2, evaluator2, _ = _service_with_repo(
        [[_same_job("indeed", url="https://indeed.com/1")]], repository=repo
    )
    report2 = await service2.run(query="Q", location="Remote", threshold=70)

    assert evaluator2.evaluate.call_count == 0  # not re-evaluated
    assert report2.qualifying_results == []  # suppressed from the report
    assert report2.reused_count == 0
    # Sighting still recorded; status not clobbered back to evaluated.
    refreshed = repo.get_job(stored.id)
    assert refreshed.status is JobStatus.APPLIED
    assert set(refreshed.seen_on) == {"indeed", "linkedin"}


@pytest.mark.asyncio
async def test_machine_status_job_is_still_reused_normally():
    """A re-scraped job whose stored status is machine-set is reused, not suppressed."""
    from src.adapters.repository.sqlite_repository import SQLiteJobRepository

    repo = SQLiteJobRepository(db_path=":memory:")
    service, _, _ = _service_with_repo(
        [[_same_job("linkedin")]],
        score_by_title={"Senior Software Engineer": 88},
        repository=repo,
    )
    await service.run(query="Q", location="Remote", threshold=70)

    service2, evaluator2, _ = _service_with_repo(
        [[_same_job("indeed", url="https://indeed.com/1")]], repository=repo
    )
    report2 = await service2.run(query="Q", location="Remote", threshold=70)

    assert evaluator2.evaluate.call_count == 0
    assert report2.reused_count == 1
    assert report2.qualifying_results[0].score == 88
