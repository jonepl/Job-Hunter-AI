"""Shared pytest fixtures available to all tests."""

from datetime import datetime

import pytest

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume


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
        matched_skills=["Python", "REST APIs"],
        missing_skills=["Kubernetes"],
        summary="Strong match with a gap in container orchestration.",
    )
