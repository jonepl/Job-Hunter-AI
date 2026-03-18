"""Unit tests for the MatchResult domain entity."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult


@pytest.fixture
def valid_job() -> Job:
    """Return a valid Job instance for use in MatchResult tests."""
    return Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="We need a Python expert...",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )


def test_match_result_valid_instantiation(valid_job: Job):
    """Happy path — MatchResult model accepts all valid required fields."""
    result = MatchResult(
        job=valid_job,
        score=85,
        matched_skills=["Python", "REST APIs"],
        missing_skills=["Kubernetes"],
        summary="Strong match with a gap in container orchestration.",
    )
    assert result.job == valid_job
    assert result.score == 85
    assert result.matched_skills == ["Python", "REST APIs"]
    assert result.missing_skills == ["Kubernetes"]
    assert result.summary == "Strong match with a gap in container orchestration."


def test_match_result_score_boundary_values(valid_job: Job):
    """Happy path — score accepts boundary values 0 and 100."""
    low = MatchResult(
        job=valid_job,
        score=0,
        matched_skills=[],
        missing_skills=["Python"],
        summary="No match.",
    )
    high = MatchResult(
        job=valid_job,
        score=100,
        matched_skills=["Python"],
        missing_skills=[],
        summary="Perfect match.",
    )
    assert low.score == 0
    assert high.score == 100


def test_match_result_score_above_100_raises_validation_error(valid_job: Job):
    """Validation failure — score above 100 raises ValidationError."""
    with pytest.raises(ValidationError):
        MatchResult(
            job=valid_job,
            score=101,
            matched_skills=["Python"],
            missing_skills=[],
            summary="Out of range.",
        )


def test_match_result_score_below_0_raises_validation_error(valid_job: Job):
    """Validation failure — score below 0 raises ValidationError."""
    with pytest.raises(ValidationError):
        MatchResult(
            job=valid_job,
            score=-1,
            matched_skills=[],
            missing_skills=["Python"],
            summary="Out of range.",
        )


def test_match_result_missing_required_field_raises_validation_error(valid_job: Job):
    """Validation failure — omitting summary raises ValidationError."""
    with pytest.raises(ValidationError):
        MatchResult(
            job=valid_job,
            score=85,
            matched_skills=["Python"],
            missing_skills=[],
            # summary is missing
        )


def test_match_result_wrong_field_type_raises_validation_error(valid_job: Job):
    """Validation failure — passing a string for score raises ValidationError."""
    with pytest.raises(ValidationError):
        MatchResult(
            job=valid_job,
            score="high",
            matched_skills=["Python"],
            missing_skills=[],
            summary="Type error test.",
        )
