"""Unit tests for src/runner.py — immediate run and result logging."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import ModelNotFoundError
from src.orchestration.runner import _log_report_results, run_immediate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(
    profile_id: int = 1, score_threshold: int = 70, enabled: bool = True
) -> MagicMock:
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
    p.enabled = enabled
    return p


def _make_report(has_qualifying: bool = True) -> MagicMock:
    """Return a minimal RunReport-like mock."""
    report = MagicMock()
    report.has_qualifying_results = has_qualifying
    report.reused_count = 0
    report.newly_evaluated_count = 0
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


@pytest.mark.asyncio
async def test_run_immediate_exits_on_model_not_found():
    """run_immediate() calls sys.exit(1) when the configured model is invalid."""
    profiles = [_make_profile(1), _make_profile(2)]
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(side_effect=ModelNotFoundError("model 'gpt-4oo' not found"))
    factory = MagicMock(return_value=mock_svc)

    with pytest.raises(SystemExit) as exc_info:
        await run_immediate(profiles=profiles, service_factory=factory)

    assert exc_info.value.code == 1
    # Fail-fast: does not fall through to the second profile.
    mock_svc.run.assert_called_once()


@pytest.mark.asyncio
async def test_run_immediate_skips_disabled_profiles(caplog):
    """A paused profile is never built or run, and the skip count is logged."""
    profiles = [_make_profile(1, enabled=False), _make_profile(2, enabled=True)]
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(return_value=_make_report())
    factory = MagicMock(return_value=mock_svc)

    with caplog.at_level(logging.INFO, logger="src.orchestration.runner"):
        await run_immediate(profiles=profiles, service_factory=factory)

    # The factory is built only for the enabled profile.
    assert factory.call_count == 1
    assert factory.call_args.args[0].profile_id == 2
    assert "Skipping 1 paused profile(s)" in " ".join(caplog.messages)


@pytest.mark.asyncio
async def test_run_immediate_stamps_last_run_running_then_succeeded():
    """A successful profile is stamped running → succeeded on the settings service."""
    profiles = [_make_profile(1)]
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(return_value=_make_report())
    settings_service = MagicMock()

    await run_immediate(
        profiles=profiles,
        service_factory=MagicMock(return_value=mock_svc),
        settings_service=settings_service,
    )

    statuses = [c.args[1] for c in settings_service.set_profile_last_run.call_args_list]
    assert statuses == ["running", "succeeded"]


@pytest.mark.asyncio
async def test_run_immediate_stamps_last_run_failed_on_error():
    """A profile that raises a generic error is stamped running → failed."""
    profiles = [_make_profile(1)]
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(side_effect=Exception("pipeline exploded"))
    settings_service = MagicMock()

    await run_immediate(
        profiles=profiles,
        service_factory=MagicMock(return_value=mock_svc),
        settings_service=settings_service,
    )

    statuses = [c.args[1] for c in settings_service.set_profile_last_run.call_args_list]
    assert statuses == ["running", "failed"]


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


def test_log_report_results_logs_dedup_summary(caplog):
    """_log_report_results() logs a 'reused / new' line when jobs were deduped."""
    profile = _make_profile()
    report = _make_report(has_qualifying=True)
    report.reused_count = 3
    report.newly_evaluated_count = 7
    test_logger = logging.getLogger("test_runner_dedup")

    with caplog.at_level(logging.INFO, logger="test_runner_dedup"):
        _log_report_results(profile, report, test_logger)

    combined = " ".join(caplog.messages)
    assert "Deduplicated: 3 reused / 7 new" in combined


def test_log_report_results_omits_dedup_when_nothing_reused(caplog):
    """_log_report_results() omits the dedup line when no jobs were reused."""
    profile = _make_profile()
    report = _make_report(has_qualifying=True)  # reused_count defaults to 0
    test_logger = logging.getLogger("test_runner_no_dedup")

    with caplog.at_level(logging.INFO, logger="test_runner_no_dedup"):
        _log_report_results(profile, report, test_logger)

    assert "Deduplicated" not in " ".join(caplog.messages)
