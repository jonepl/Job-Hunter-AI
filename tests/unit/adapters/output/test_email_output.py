"""Unit tests for the email output adapter."""

import smtplib
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.output.email_output import EmailOutput
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult


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
