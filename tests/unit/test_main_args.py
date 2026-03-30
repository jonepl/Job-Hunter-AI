"""Unit tests for CLI argument parsing and location resolution in main.py."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.domain.scraper_name import ScraperName
from src.main import _parse_args, _resolve_location, main


def test_location_defaults_to_united_states_for_remote():
    """Remote only, no --location → resolved location is 'United States'."""
    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "remote"]):
        args = _parse_args()
    location, defaulted, _ = _resolve_location(args)
    assert location == "United States"
    assert defaulted is True


def test_location_used_as_provided_for_remote():
    """Remote only, --location provided → resolved location is the provided value."""
    with patch("sys.argv", ["prog", "--query", "SE", "--location", "New York", "--work-type", "remote"]):
        args = _parse_args()
    location, defaulted, _ = _resolve_location(args)
    assert location == "New York"
    assert defaulted is False


def test_location_required_for_hybrid_no_location():
    """Hybrid work type with no --location → sys.exit(1) with error message."""
    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "hybrid"]):
        args = _parse_args()
    with patch("builtins.print") as mock_print:
        with pytest.raises(SystemExit) as exc_info:
            _resolve_location(args)
    assert exc_info.value.code == 1
    printed = " ".join(str(call) for call in mock_print.call_args_list)
    assert "--location is required" in printed


def test_location_required_for_onsite_no_location():
    """Onsite work type with no --location → sys.exit(1)."""
    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "onsite"]):
        args = _parse_args()
    with pytest.raises(SystemExit) as exc_info:
        _resolve_location(args)
    assert exc_info.value.code == 1


def test_location_required_when_no_work_type():
    """No --work-type and no --location → sys.exit(1) with error message."""
    with patch("sys.argv", ["prog", "--query", "SE"]):
        args = _parse_args()
    with patch("builtins.print") as mock_print:
        with pytest.raises(SystemExit) as exc_info:
            _resolve_location(args)
    assert exc_info.value.code == 1
    printed = " ".join(str(call) for call in mock_print.call_args_list)
    assert "--location is required" in printed


def test_location_used_when_provided_no_work_type():
    """No --work-type, --location provided → resolved location is the provided value."""
    with patch("sys.argv", ["prog", "--query", "SE", "--location", "Remote"]):
        args = _parse_args()
    location, defaulted, _ = _resolve_location(args)
    assert location == "Remote"
    assert defaulted is False


def test_location_required_for_remote_hybrid_mix():
    """Mixed remote+hybrid with no --location → sys.exit(1)."""
    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "remote", "hybrid"]):
        args = _parse_args()
    with pytest.raises(SystemExit) as exc_info:
        _resolve_location(args)
    assert exc_info.value.code == 1


def test_location_provided_for_remote_hybrid_mix():
    """Mixed remote+hybrid with --location provided → resolved location is the provided value."""
    with patch("sys.argv", ["prog", "--query", "SE", "--location", "New York", "--work-type", "remote", "hybrid"]):
        args = _parse_args()
    location, defaulted, _ = _resolve_location(args)
    assert location == "New York"
    assert defaulted is False


# ---------------------------------------------------------------------------
# Scraper selection tests
# ---------------------------------------------------------------------------

# Minimal env required to get past _require_env / env loading in main()
_BASE_ENV = {
    "GMAIL_ADDRESS": "test@gmail.com",
    "GMAIL_APP_PASSWORD": "testpassword",
    "EMAIL_RECIPIENT": "r@example.com",
    "SCORE_THRESHOLD": "70",
    "DATE_POSTED": "3days",
}


def _make_report_mock() -> MagicMock:
    """Return a minimal RunReport-like mock for main() success path."""
    mock = MagicMock()
    mock.has_qualifying_results = False
    mock.qualifying_results = []
    mock.near_miss_results = []
    mock.suggested_threshold = None
    return mock


@pytest.mark.asyncio
async def test_scrapers_loaded_from_env():
    """ACTIVE_SCRAPERS=linkedin,indeed in env → build_scrapers called with two names."""
    env = {**_BASE_ENV, "ACTIVE_SCRAPERS": "linkedin,indeed"}
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(return_value=_make_report_mock())

    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "remote"]), \
         patch.dict("os.environ", env, clear=False), \
         patch("src.main.load_dotenv"), \
         patch("src.main._configure_logging"), \
         patch("src.main.build_scrapers", return_value=[]) as mock_build, \
         patch("src.main.build_evaluator", return_value=MagicMock()), \
         patch("src.main.EmailOutput", return_value=MagicMock()), \
         patch("src.main.FileOutput", return_value=MagicMock()), \
         patch("src.main.JobSearchService", return_value=mock_svc):
        await main()

    mock_build.assert_called_once_with([ScraperName.LINKEDIN, ScraperName.INDEED])


@pytest.mark.asyncio
async def test_scrapers_cli_overrides_env():
    """--scrapers indeed via CLI overrides ACTIVE_SCRAPERS=linkedin in env."""
    env = {**_BASE_ENV, "ACTIVE_SCRAPERS": "linkedin"}
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(return_value=_make_report_mock())

    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "remote", "--scrapers", "indeed"]), \
         patch.dict("os.environ", env, clear=False), \
         patch("src.main.load_dotenv"), \
         patch("src.main._configure_logging"), \
         patch("src.main.build_scrapers", return_value=[]) as mock_build, \
         patch("src.main.build_evaluator", return_value=MagicMock()), \
         patch("src.main.EmailOutput", return_value=MagicMock()), \
         patch("src.main.FileOutput", return_value=MagicMock()), \
         patch("src.main.JobSearchService", return_value=mock_svc):
        await main()

    mock_build.assert_called_once_with([ScraperName.INDEED])


@pytest.mark.asyncio
async def test_scrapers_invalid_name_exits():
    """--scrapers linkedin,monster → sys.exit(1) with 'Invalid scraper name' message."""
    env = {**_BASE_ENV}

    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "remote", "--scrapers", "linkedin,monster"]), \
         patch.dict("os.environ", env, clear=False), \
         patch("src.main.load_dotenv"), \
         patch("src.main._configure_logging"), \
         patch("builtins.print") as mock_print:
        with pytest.raises(SystemExit) as exc_info:
            await main()

    assert exc_info.value.code == 1
    printed = " ".join(str(c) for c in mock_print.call_args_list)
    assert "Invalid scraper name" in printed


@pytest.mark.asyncio
async def test_scrapers_empty_string_exits():
    """--scrapers '' (empty string) → sys.exit(1) because no valid scrapers remain."""
    env = {**_BASE_ENV}

    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "remote", "--scrapers", ""]), \
         patch.dict("os.environ", env, clear=False), \
         patch("src.main.load_dotenv"), \
         patch("src.main._configure_logging"), \
         patch("builtins.print"):
        with pytest.raises(SystemExit) as exc_info:
            await main()

    assert exc_info.value.code == 1
