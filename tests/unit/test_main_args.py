"""Unit tests for CLI argument parsing and profile overrides in main.py."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli.args import parse_args
from src.core.domain.scraper_name import ScraperName
from src.main import main


# ---------------------------------------------------------------------------
# CLI argument parsing tests
# ---------------------------------------------------------------------------


def test_parse_args_query_optional():
    """--query is optional in the new profile-based design."""
    with patch("sys.argv", ["prog"]):
        args = parse_args()
    assert args.query is None


def test_parse_args_query_accepted():
    """--query value is parsed correctly."""
    with patch("sys.argv", ["prog", "--query", "Senior Engineer"]):
        args = parse_args()
    assert args.query == "Senior Engineer"


def test_parse_args_location_optional():
    """--location is optional — can come from .env."""
    with patch("sys.argv", ["prog"]):
        args = parse_args()
    assert args.location is None


def test_parse_args_work_type_accepted():
    """--work-type accepts one or more valid values."""
    with patch("sys.argv", ["prog", "--work-type", "remote"]):
        args = parse_args()
    assert args.work_type == ["remote"]


def test_parse_args_date_posted_accepted():
    """--date-posted value is stored under date_posted attribute."""
    with patch("sys.argv", ["prog", "--date-posted", "week"]):
        args = parse_args()
    assert args.date_posted == "week"


def test_parse_args_scrapers_accepted():
    """--scrapers value is stored as a raw string."""
    with patch("sys.argv", ["prog", "--scrapers", "linkedin,indeed"]):
        args = parse_args()
    assert args.scrapers == "linkedin,indeed"


# ---------------------------------------------------------------------------
# Integration tests for main() — profile loading and CLI overrides
# ---------------------------------------------------------------------------

# Minimal env required to load a legacy single profile via SEARCH_QUERY
_BASE_ENV = {
    "SEARCH_QUERY": "Senior Engineer",
    "WORK_TYPE": "remote",
    "SCHEDULE_ENABLED": "false",
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
async def test_scrapers_cli_overrides_env(tmp_path):
    """--scrapers indeed via CLI overrides ACTIVE_SCRAPERS in env."""
    env = {**_BASE_ENV, "ACTIVE_SCRAPERS": "linkedin", "DB_PATH": str(tmp_path / "a.db")}
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(return_value=_make_report_mock())

    captured_profiles = []

    def capture_build_service(profile):
        captured_profiles.append(profile)
        return mock_svc

    with patch("sys.argv", ["prog", "--scrapers", "indeed"]), \
         patch.dict("os.environ", env, clear=True), \
         patch("src.main.load_dotenv"), \
         patch("src.main.configure_logging"), \
         patch("src.main.build_service", side_effect=capture_build_service):
        await main()

    assert len(captured_profiles) == 1
    assert captured_profiles[0].active_scrapers == [ScraperName.INDEED]


@pytest.mark.asyncio
async def test_scrapers_invalid_name_exits(tmp_path):
    """--scrapers linkedin,monster → sys.exit(1) with 'Invalid scraper name' message."""
    env = {**_BASE_ENV, "DB_PATH": str(tmp_path / "a.db")}

    with patch("sys.argv", ["prog", "--scrapers", "linkedin,monster"]), \
         patch.dict("os.environ", env, clear=True), \
         patch("src.main.load_dotenv"), \
         patch("src.main.configure_logging"), \
         patch("builtins.print") as mock_print:
        with pytest.raises(SystemExit) as exc_info:
            await main()

    assert exc_info.value.code == 1
    printed = " ".join(str(c) for c in mock_print.call_args_list)
    assert "Invalid scraper name" in printed


@pytest.mark.asyncio
async def test_scrapers_empty_string_exits(tmp_path):
    """--scrapers '' (empty string) → sys.exit(1) due to empty parse result."""
    env = {**_BASE_ENV, "DB_PATH": str(tmp_path / "a.db")}

    with patch("sys.argv", ["prog", "--scrapers", ""]), \
         patch.dict("os.environ", env, clear=True), \
         patch("src.main.load_dotenv"), \
         patch("src.main.configure_logging"), \
         patch("builtins.print"):
        with pytest.raises(SystemExit) as exc_info:
            await main()

    assert exc_info.value.code == 1


@pytest.mark.asyncio
async def test_query_cli_overrides_env(tmp_path):
    """--query via CLI overrides profile.query for all profiles."""
    env = {**_BASE_ENV, "DB_PATH": str(tmp_path / "a.db")}
    mock_svc = MagicMock()
    mock_svc.run = AsyncMock(return_value=_make_report_mock())

    captured_profiles = []

    def capture_build_service(profile):
        captured_profiles.append(profile)
        return mock_svc

    with patch("sys.argv", ["prog", "--query", "Full Stack Engineer"]), \
         patch.dict("os.environ", env, clear=True), \
         patch("src.main.load_dotenv"), \
         patch("src.main.configure_logging"), \
         patch("src.main.build_service", side_effect=capture_build_service):
        await main()

    assert captured_profiles[0].query == "Full Stack Engineer"
