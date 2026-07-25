"""Unit tests for the RunReport domain model."""

from datetime import datetime

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


def test_suggested_threshold_is_near_miss_floor():
    """suggested_threshold is the fixed near-miss floor, not floor-the-lowest (ADR-033)."""
    near_misses = [
        _make_match_result(68),
        _make_match_result(64),
        _make_match_result(61),
    ]
    # threshold 70, default band 15 → near_miss_floor = 55, independent of scores.
    report = _make_report(score_threshold=70, near_miss_results=near_misses)
    assert report.near_miss_floor == 55
    assert report.suggested_threshold == 55


def test_suggested_threshold_respects_custom_band():
    """near_miss_floor tracks the configured NEAR_MISS_BAND."""
    report = _make_report(
        score_threshold=80,
        near_miss_band=10,
        near_miss_results=[_make_match_result(72)],
    )
    assert report.suggested_threshold == 70


def test_near_miss_floor_never_negative():
    """near_miss_floor floors at 0 when the band exceeds the threshold."""
    report = _make_report(score_threshold=10, near_miss_band=15)
    assert report.near_miss_floor == 0


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


def test_newly_evaluated_count_subtracts_reused():
    """newly_evaluated_count is total_evaluated minus reused_count."""
    report = _make_report(total_evaluated=10, reused_count=4)
    assert report.newly_evaluated_count == 6


def test_newly_evaluated_count_defaults_to_total():
    """newly_evaluated_count equals total_evaluated when nothing was reused."""
    report = _make_report(total_evaluated=7)
    assert report.reused_count == 0
    assert report.newly_evaluated_count == 7


def test_newly_evaluated_count_never_negative():
    """newly_evaluated_count floors at 0 if reused_count somehow exceeds total."""
    report = _make_report(total_evaluated=3, reused_count=5)
    assert report.newly_evaluated_count == 0
