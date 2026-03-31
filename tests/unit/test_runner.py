"""Unit tests for src/runner.py — immediate run and result logging."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.runner import _log_report_results, run_immediate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(profile_id: int = 1, score_threshold: int = 70) -> MagicMock:
    """Return a minimal SearchProfile-like mock."""
    p = MagicMock()
    p.profile_id = profile_id
    p.query = "Software Engineer"
    p.location = "Remote"
    p.score_threshold = score_threshold
    p.top_results = None
    p.work_types = []
    p.date_posted = None
    p.active_scrapers = []
    return p


def _make_report(has_qualifying: bool = True) -> MagicMock:
    """Return a minimal RunReport-like mock."""
    report = MagicMock()
    report.has_qualifying_results = has_qualifying
    if has_qualifying:
        result = MagicMock()
        result.score = 85
        result.job.title = "Senior Engineer"
        result.job.company = "Acme"
        result.job.platform = "linkedin"
        result.hire_recommendation = "Strong Yes"
        report.qualifying_results = [result]
        report.near_miss_results = []
    else:
        report.qualifying_results = []
        near_miss = MagicMock()
        near_miss.score = 60
        near_miss.job.title = "Engineer"
        near_miss.job.company = "Corp"
        report.near_miss_results = [near_miss]
        report.suggested_threshold = 55
    return report


# ---------------------------------------------------------------------------
# run_immediate tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_immediate_runs_all_profiles():
    """run_immediate() calls service.run() once per profile."""
    profiles = [_make_profile(1), _make_profile(2)]
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(return_value=_make_report())
    factory = MagicMock(return_value=mock_svc)

    await run_immediate(profiles=profiles, service_factory=factory)

    assert mock_svc.run.call_count == 2


@pytest.mark.asyncio
async def test_run_immediate_continues_on_profile_error():
    """run_immediate() continues to next profile when a generic Exception is raised."""
    profiles = [_make_profile(1), _make_profile(2)]

    first_svc = MagicMock()
    first_svc.run = AsyncMock(side_effect=Exception("pipeline exploded"))

    second_svc = MagicMock()
    second_svc.run = AsyncMock(return_value=_make_report())

    factory = MagicMock(side_effect=[first_svc, second_svc])

    await run_immediate(profiles=profiles, service_factory=factory)

    second_svc.run.assert_called_once()


@pytest.mark.asyncio
async def test_run_immediate_exits_on_resume_not_found():
    """run_immediate() calls sys.exit(1) when FileNotFoundError is raised."""
    profiles = [_make_profile(1)]
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(side_effect=FileNotFoundError("resume.pdf missing"))
    factory = MagicMock(return_value=mock_svc)

    with pytest.raises(SystemExit) as exc_info:
        await run_immediate(profiles=profiles, service_factory=factory)

    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# _log_report_results tests
# ---------------------------------------------------------------------------


def test_log_report_results_qualifying(caplog):
    """_log_report_results() logs score, title, and company for qualifying results."""
    profile = _make_profile()
    report = _make_report(has_qualifying=True)
    test_logger = logging.getLogger("test_runner_qualifying")

    with caplog.at_level(logging.INFO, logger="test_runner_qualifying"):
        _log_report_results(profile, report, test_logger)

    combined = " ".join(caplog.messages)
    assert "85" in combined
    assert "Senior Engineer" in combined
    assert "Acme" in combined


def test_log_report_results_zero_qualifying(caplog):
    """_log_report_results() warns about 0 qualifying results and suggests threshold."""
    profile = _make_profile()
    report = _make_report(has_qualifying=False)
    test_logger = logging.getLogger("test_runner_zero")

    with caplog.at_level(logging.WARNING, logger="test_runner_zero"):
        _log_report_results(profile, report, test_logger)

    combined = " ".join(caplog.messages)
    assert "0 qualifying results" in combined
    assert "55" in combined
