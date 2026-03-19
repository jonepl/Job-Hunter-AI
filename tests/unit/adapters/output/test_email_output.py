"""Unit tests for the email output adapter."""

import smtplib
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.output.email_output import EmailOutput
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory


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


@pytest.fixture
def sample_results() -> list[MatchResult]:
    """Return a list of MatchResult fixtures."""
    job = Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="Python role.",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )
    return [
        MatchResult(
            job=job,
            score=85,
            seniority_level="Senior/Staff",
            years_experience_detected=7,
            hire_recommendation="Strong Yes",
            score_breakdown=_make_score_breakdown(),
            matched_skills=["Python", "REST APIs"],
            missing_skills=["Kubernetes"],
            summary="Strong match.",
        )
    ]


@pytest.mark.asyncio
async def test_deliver_sends_email_via_smtp(sample_results):
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
        await output.deliver(sample_results)

    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("sender@gmail.com", "app-password")
    mock_smtp.sendmail.assert_called_once()


@pytest.mark.asyncio
async def test_deliver_does_nothing_when_results_empty():
    """Edge case — deliver() exits early and does not open SMTP for empty results."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )

    with patch("src.adapters.output.email_output.smtplib.SMTP") as mock_smtp_cls:
        await output.deliver([])

    mock_smtp_cls.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_handles_smtp_auth_error_gracefully(sample_results):
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
        await output.deliver(sample_results)  # must not raise


def test_build_html_contains_hire_recommendation(sample_results):
    """Happy path — HTML body includes the hire_recommendation value."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(sample_results)
    assert "Strong Yes" in html


def test_build_html_contains_score_breakdown_table(sample_results):
    """Happy path — HTML body includes score breakdown table with category names."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(sample_results)
    assert "Score Breakdown" in html
    assert "Role Alignment" in html
    assert "Technical Stack Match" in html
    assert "Career Trajectory" in html


def test_build_html_contains_seniority_and_experience(sample_results):
    """Happy path — HTML body includes seniority level and experience detected."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(sample_results)
    assert "Senior/Staff" in html
    assert "7 years" in html


def test_build_html_contains_job_link(sample_results):
    """Happy path — HTML body includes a link to the job posting."""
    output = EmailOutput(
        sender="sender@gmail.com",
        password="app-password",
        recipient="recipient@example.com",
    )
    html = output._build_html(sample_results)
    assert "https://linkedin.com/jobs/123" in html
