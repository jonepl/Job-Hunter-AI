"""Shared pytest fixtures available to all tests."""

from datetime import datetime

import pytest

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.resume import Resume
from src.core.domain.run_report import RunReport


@pytest.fixture
def sample_job() -> Job:
    """Return a valid Job fixture for use across all test modules."""
    return Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="We need a Python expert...",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )


@pytest.fixture
def sample_resume() -> Resume:
    """Return a valid Resume fixture for use across all test modules."""
    return Resume(
        raw_text="Experienced Python developer with 5 years...",
        parsed_at=datetime(2026, 3, 17, 9, 0, 0),
    )


@pytest.fixture
def sample_match_result(sample_job: Job) -> MatchResult:
    """Return a valid MatchResult fixture for use across all test modules."""
    return MatchResult(
        job=sample_job,
        score=85,
        seniority_level="Senior/Staff",
        years_experience_detected=7,
        hire_recommendation="Strong Yes",
        score_breakdown=ScoreBreakdown(
            role_alignment=ScoreCategory(
                max=20,
                earned=18,
                reasoning="Strong alignment with senior Python role requirements.",
            ),
            technical_stack_match=ScoreCategory(
                max=15,
                earned=13,
                reasoning="Python, REST APIs, and Django all present.",
            ),
            system_design_architecture=ScoreCategory(
                max=15,
                earned=11,
                reasoning="Solid system design background demonstrated.",
            ),
            impact_and_metrics=ScoreCategory(
                max=15,
                earned=12,
                reasoning="Clear business impact with quantified metrics.",
            ),
            domain_industry_experience=ScoreCategory(
                max=10,
                earned=8,
                reasoning="Relevant SaaS domain experience.",
            ),
            problem_space_relevance=ScoreCategory(
                max=10,
                earned=7,
                reasoning="Matching problem space in backend services.",
            ),
            ownership_and_leadership=ScoreCategory(
                max=10,
                earned=9,
                reasoning="Led multiple cross-team initiatives.",
            ),
            resume_signal_quality=ScoreCategory(
                max=3,
                earned=3,
                reasoning="Well-structured resume with clear progression.",
            ),
            career_trajectory=ScoreCategory(
                max=2,
                earned=2,
                reasoning="Consistent upward trajectory.",
            ),
        ),
        matched_skills=["Python", "REST APIs"],
        missing_skills=["Kubernetes"],
        summary="Strong match with a gap in container orchestration.",
    )


@pytest.fixture
def sample_run_report(sample_match_result: MatchResult) -> RunReport:
    """Return a valid RunReport fixture with one qualifying result."""
    return RunReport(
        qualifying_results=[sample_match_result],
        near_miss_results=[],
        total_evaluated=5,
        score_threshold=70,
        top_results=None,
        query="Senior Python Developer",
        location="Remote",
        run_at=datetime(2026, 3, 17, 9, 0, 0),
    )
