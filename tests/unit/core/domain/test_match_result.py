"""Unit tests for the MatchResult domain entity."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory


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


def _make_score_breakdown() -> ScoreBreakdown:
    """Return a valid ScoreBreakdown for use in MatchResult tests."""
    return ScoreBreakdown(
        role_alignment=ScoreCategory(max=20, earned=16, reasoning="Good role alignment."),
        technical_stack_match=ScoreCategory(max=15, earned=12, reasoning="Strong stack match."),
        system_design_architecture=ScoreCategory(max=15, earned=10, reasoning="Solid design."),
        impact_and_metrics=ScoreCategory(max=15, earned=11, reasoning="Clear impact."),
        domain_industry_experience=ScoreCategory(max=10, earned=8, reasoning="Relevant domain."),
        problem_space_relevance=ScoreCategory(max=10, earned=7, reasoning="On point."),
        ownership_and_leadership=ScoreCategory(max=10, earned=8, reasoning="Strong ownership."),
        resume_signal_quality=ScoreCategory(max=3, earned=3, reasoning="Clean resume."),
        career_trajectory=ScoreCategory(max=2, earned=2, reasoning="Upward trajectory."),
    )


# --- ScoreCategory tests ---


def test_score_category_valid_instantiation():
    """Happy path — ScoreCategory accepts valid max, earned, and reasoning."""
    cat = ScoreCategory(max=20, earned=15, reasoning="Good match.")
    assert cat.max == 20
    assert cat.earned == 15
    assert cat.reasoning == "Good match."


def test_score_category_missing_field_raises_validation_error():
    """Validation failure — omitting reasoning raises ValidationError."""
    with pytest.raises(ValidationError):
        ScoreCategory(max=20, earned=15)  # type: ignore[call-arg]


def test_score_category_wrong_type_raises_validation_error():
    """Validation failure — passing a string for earned raises ValidationError."""
    with pytest.raises(ValidationError):
        ScoreCategory(max=20, earned="high", reasoning="test")  # type: ignore[arg-type]


# --- ScoreBreakdown tests ---


def test_score_breakdown_valid_instantiation():
    """Happy path — ScoreBreakdown accepts all nine valid ScoreCategory fields."""
    bd = _make_score_breakdown()
    assert bd.role_alignment.max == 20
    assert bd.technical_stack_match.earned == 12
    assert bd.career_trajectory.reasoning == "Upward trajectory."


def test_score_breakdown_missing_category_raises_validation_error():
    """Validation failure — omitting a required category raises ValidationError."""
    with pytest.raises(ValidationError):
        ScoreBreakdown(
            role_alignment=ScoreCategory(max=20, earned=16, reasoning="ok"),
            # remaining categories omitted
        )  # type: ignore[call-arg]


# --- MatchResult tests ---


def test_match_result_valid_instantiation(valid_job: Job):
    """Happy path — MatchResult model accepts all valid required fields."""
    result = MatchResult(
        job=valid_job,
        score=85,
        seniority_level="Senior/Staff",
        years_experience_detected=7,
        hire_recommendation="Strong Yes",
        score_breakdown=_make_score_breakdown(),
        matched_skills=["Python", "REST APIs"],
        missing_skills=["Kubernetes"],
        summary="Strong match with a gap in container orchestration.",
    )
    assert result.job == valid_job
    assert result.score == 85
    assert result.seniority_level == "Senior/Staff"
    assert result.years_experience_detected == 7
    assert result.hire_recommendation == "Strong Yes"
    assert result.matched_skills == ["Python", "REST APIs"]
    assert result.missing_skills == ["Kubernetes"]
    assert result.summary == "Strong match with a gap in container orchestration."


def test_match_result_with_all_new_fields(valid_job: Job):
    """Happy path — MatchResult correctly stores all four new fields."""
    bd = _make_score_breakdown()
    result = MatchResult(
        job=valid_job,
        score=72,
        seniority_level="Mid-Level",
        years_experience_detected=4,
        hire_recommendation="Yes",
        score_breakdown=bd,
        matched_skills=["Python"],
        missing_skills=["Go"],
        summary="Solid mid-level match.",
    )
    assert result.seniority_level == "Mid-Level"
    assert result.years_experience_detected == 4
    assert result.hire_recommendation == "Yes"
    assert result.score_breakdown.role_alignment.earned == 16


def test_match_result_years_experience_detected_accepts_none(valid_job: Job):
    """Happy path — years_experience_detected accepts None."""
    result = MatchResult(
        job=valid_job,
        score=60,
        seniority_level="Junior",
        years_experience_detected=None,
        hire_recommendation="Borderline",
        score_breakdown=_make_score_breakdown(),
        matched_skills=[],
        missing_skills=["Python"],
        summary="Limited match.",
    )
    assert result.years_experience_detected is None


def test_match_result_score_boundary_values(valid_job: Job):
    """Happy path — score accepts boundary values 0 and 100."""
    low = MatchResult(
        job=valid_job,
        score=0,
        seniority_level="Unknown",
        years_experience_detected=None,
        hire_recommendation="No",
        score_breakdown=_make_score_breakdown(),
        matched_skills=[],
        missing_skills=["Python"],
        summary="No match.",
    )
    high = MatchResult(
        job=valid_job,
        score=100,
        seniority_level="Senior/Staff",
        years_experience_detected=10,
        hire_recommendation="Strong Yes",
        score_breakdown=_make_score_breakdown(),
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
            seniority_level="Senior/Staff",
            years_experience_detected=7,
            hire_recommendation="Strong Yes",
            score_breakdown=_make_score_breakdown(),
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
            seniority_level="Junior",
            years_experience_detected=None,
            hire_recommendation="No",
            score_breakdown=_make_score_breakdown(),
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
            seniority_level="Senior/Staff",
            years_experience_detected=7,
            hire_recommendation="Strong Yes",
            score_breakdown=_make_score_breakdown(),
            matched_skills=["Python"],
            missing_skills=[],
            # summary is missing
        )  # type: ignore[call-arg]


def test_match_result_wrong_field_type_raises_validation_error(valid_job: Job):
    """Validation failure — passing a string for score raises ValidationError."""
    with pytest.raises(ValidationError):
        MatchResult(
            job=valid_job,
            score="high",  # type: ignore[arg-type]
            seniority_level="Senior/Staff",
            years_experience_detected=7,
            hire_recommendation="Strong Yes",
            score_breakdown=_make_score_breakdown(),
            matched_skills=["Python"],
            missing_skills=[],
            summary="Type error test.",
        )
