"""Unit tests for the RunReport domain model."""

from datetime import datetime

import pytest

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.run_report import RunReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_score_breakdown() -> ScoreBreakdown:
    """Return a minimal valid ScoreBreakdown."""
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


def _make_match_result(score: int) -> MatchResult:
    """Return a MatchResult with the given score."""
    job = Job(
        title="Engineer",
        company="Acme",
        location="Remote",
        url="https://example.com/jobs/1",
        description="A job description.",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )
    return MatchResult(
        job=job,
        score=score,
        seniority_level="Mid-Level",
        years_experience_detected=None,
        hire_recommendation="Yes",
        score_breakdown=_make_score_breakdown(),
        matched_skills=["Python"],
        missing_skills=[],
        summary="Test result.",
    )


def _make_report(**kwargs) -> RunReport:
    """Return a RunReport with sensible defaults, overridable via kwargs."""
    defaults = dict(
        qualifying_results=[],
        near_miss_results=[],
        total_evaluated=10,
        score_threshold=70,
        top_results=None,
        query="Senior Python Developer",
        location="Remote",
        run_at=datetime(2026, 3, 17, 9, 0, 0),
    )
    return RunReport(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_has_qualifying_results_true():
    """has_qualifying_results returns True when qualifying_results is populated."""
    report = _make_report(qualifying_results=[_make_match_result(80)])
    assert report.has_qualifying_results is True


def test_has_qualifying_results_false():
    """has_qualifying_results returns False when qualifying_results is empty."""
    report = _make_report(qualifying_results=[])
    assert report.has_qualifying_results is False


def test_suggested_threshold_rounds_down_to_five():
    """suggested_threshold floors the lowest near-miss score to nearest 5."""
    near_misses = [
        _make_match_result(79),
        _make_match_result(76),
        _make_match_result(74),
    ]
    report = _make_report(near_miss_results=near_misses)
    # min score is 74 → 74 // 5 * 5 = 70
    assert report.suggested_threshold == 70


def test_suggested_threshold_none_when_no_near_misses():
    """suggested_threshold returns None when near_miss_results is empty."""
    report = _make_report(near_miss_results=[])
    assert report.suggested_threshold is None


def test_near_misses_empty_when_qualifying_exist():
    """RunReport with qualifying_results has empty near_miss_results."""
    report = _make_report(
        qualifying_results=[_make_match_result(80)],
        near_miss_results=[],
    )
    assert report.near_miss_results == []


def test_top_results_field_accepts_none():
    """RunReport validates successfully when top_results is None."""
    report = _make_report(top_results=None)
    assert report.top_results is None
