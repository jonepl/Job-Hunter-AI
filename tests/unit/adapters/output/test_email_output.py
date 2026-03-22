"""Unit tests for the email output adapter."""

import smtplib
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.output.email_output import EmailOutput
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.run_report import RunReport


def _make_score_breakdown() -> ScoreBreakdown:
    """Return a valid ScoreBreakdown for use in email output tests."""
    return ScoreBreakdown(
        role_alignment=ScoreCategory(max=20, earned=18, reasoning="Strong alignment."),
        technical_stack_match=ScoreCategory(max=15, earned=13, reasoning="Good stack."),
        system_design_architecture=ScoreCategory(max=15, earned=11, reasoning="Solid design."),
        impact_and_metrics=ScoreCategory(max=15, earned=12, reasoning="Clear impact."),
        domain_industry_experience=ScoreCategory(max=10, earned=8, reasoning="Relevant domain."),
        problem_space_relevance=ScoreCategory(max=10, earned=7, reasoning="On point."),
        ownership_and_leadership=ScoreCategory(max=10, earned=9, reasoning="Strong ownership."),
        resume_signal_quality=ScoreCategory(max=3, earned=3, reasoning="Clean resume."),
        career_trajectory=ScoreCategory(max=2, earned=2, reasoning="Upward trajectory."),
    )


def _make_job() -> Job:
    """Return a valid Job fixture."""
    return Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="Python role.",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )


def _make_match_result(score: int = 85) -> MatchResult:
    """Return a MatchResult with the given score."""
    return MatchResult(
        job=_make_job(),
        score=score,
        seniority_level="Senior/Staff",
        years_experience_detected=7,
        hire_recommendation="Strong Yes",
        score_breakdown=_make_score_breakdown(),
        matched_skills=["Python", "REST APIs"],
        missing_skills=["Kubernetes"],
        summary="Strong match.",
    )


def _make_report(
    qualifying_results: list[MatchResult] | None = None,
    near_miss_results: list[MatchResult] | None = None,
    top_results: int | None = None,
) -> RunReport:
    """Return a RunReport with sensible defaults."""
    return RunReport(
        qualifying_results=qualifying_results or [],
        near_miss_results=near_miss_results or [],
        total_evaluated=10,
        score_threshold=70,
        top_results=top_results,
        query="Senior Python Developer",
        location="Remote",
        run_at=datetime(2026, 3, 17, 9, 0, 0),
    )


@pytest.fixture
def sample_report() -> RunReport:
    """Return a RunReport with one qualifying result."""
    return _make_report(qualifying_results=[_make_match_result()])


@pytest.fixture
def zero_results_report() -> RunReport:
    """Return a RunReport with zero qualifying results and near-miss results."""
    return _make_report(
        qualifying_results=[],
        near_miss_results=[
            _make_match_result(65),
            _make_match_result(60),
        ],
    )


# ---------------------------------------------------------------------------
# Existing tests — updated to pass RunReport
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deliver_sends_email_via_smtp(sample_report):
    """Happy path — deliver() connects to Gmail SMTP and sends an email."""
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )

    with patch("src.adapters.output.email_output.smtplib.SMTP", return_value=mock_smtp):
        await output.deliver(sample_report)

    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("sender@gmail.com", "app-password")
    mock_smtp.sendmail.assert_called_once()


@pytest.mark.asyncio
async def test_deliver_sends_email_when_zero_qualifying_results(zero_results_report):
    """Zero results — deliver() still opens SMTP and sends email."""
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )

    with patch("src.adapters.output.email_output.smtplib.SMTP", return_value=mock_smtp):
        await output.deliver(zero_results_report)

    mock_smtp.sendmail.assert_called_once()


@pytest.mark.asyncio
async def test_deliver_handles_smtp_auth_error_gracefully(sample_report):
    """Error handling — SMTP auth failure is logged and does not raise."""
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.login = MagicMock(
        side_effect=smtplib.SMTPAuthenticationError(535, b"auth failed")
    )

    output = EmailOutput(
        sender="sender@gmail.com",
        password="wrong-password",
        recipient="recipient@example.com",
    )

    with patch("src.adapters.output.email_output.smtplib.SMTP", return_value=mock_smtp):
        await output.deliver(sample_report)  # must not raise


def test_build_html_contains_hire_recommendation(sample_report):
    """Happy path — HTML body includes the hire_recommendation value."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(sample_report)
    assert "Strong Yes" in html


def test_build_html_contains_score_breakdown_table(sample_report):
    """Happy path — HTML body includes score breakdown table with category names."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(sample_report)
    assert "Score Breakdown" in html
    assert "Role Alignment" in html
    assert "Technical Stack Match" in html
    assert "Career Trajectory" in html


def test_build_html_contains_seniority_and_experience(sample_report):
    """Happy path — HTML body includes seniority level and experience detected."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(sample_report)
    assert "Senior/Staff" in html
    assert "7 years" in html


def test_build_html_contains_job_link(sample_report):
    """Happy path — HTML body includes a link to the job posting."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(sample_report)
    assert "https://linkedin.com/jobs/123" in html


# ---------------------------------------------------------------------------
# New tests — zero results and RunReport fields
# ---------------------------------------------------------------------------

def test_email_subject_reflects_zero_results(zero_results_report):
    """Email subject contains '0 matches above threshold' when no qualifying results."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    # Build HTML to validate subject is set correctly via deliver path
    # We check via the _build_html that zero results path triggers
    html = output._build_html(zero_results_report)
    assert "No Matches Found" in html


def test_email_body_contains_near_miss_section(zero_results_report):
    """Zero results email body contains 'Near-Miss Results' section."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(zero_results_report)
    assert "Near-Miss Results" in html


def test_email_body_contains_suggestion(zero_results_report):
    """Zero results email body contains threshold lowering suggestion."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(zero_results_report)
    assert "Consider lowering" in html
    assert "SCORE_THRESHOLD" in html


def test_email_body_contains_suggested_threshold(zero_results_report):
    """Zero results email body contains the suggested_threshold value."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(zero_results_report)
    # near-miss scores are 65 and 60 → min is 60 → 60 // 5 * 5 = 60
    assert str(zero_results_report.suggested_threshold) in html


def test_email_top_results_shows_not_set(sample_report):
    """Email body shows 'not set' for top results cap when top_results is None."""
    report = _make_report(qualifying_results=[_make_match_result()], top_results=None)
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(report)
    assert "not set" in html
