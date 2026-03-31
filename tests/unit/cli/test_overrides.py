"""Unit tests for src/cli/overrides.py — CLI override application."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from src.cli.overrides import apply_cli_overrides
from src.core.domain.work_type import WorkType


def _make_args(**kwargs) -> argparse.Namespace:
    """Build a Namespace with all override fields defaulting to None."""
    defaults = {
        "query": None,
        "location": None,
        "work_type": None,
        "date_posted": None,
        "scrapers": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_profile(query: str = "original", location: str = "New York") -> MagicMock:
    """Return a minimal SearchProfile-like mock."""
    p = MagicMock()
    p.query = query
    p.location = location
    return p


def test_apply_query_override():
    """args.query overrides profile.query on all profiles."""
    profiles = [_make_profile(query="original"), _make_profile(query="original")]
    args = _make_args(query="overridden")
    apply_cli_overrides(profiles, args)
    for p in profiles:
        assert p.query == "overridden"


def test_apply_work_type_override():
    """args.work_type is converted to WorkType enum and applied to all profiles."""
    profiles = [_make_profile()]
    args = _make_args(work_type=["remote"])
    apply_cli_overrides(profiles, args)
    assert profiles[0].work_types == [WorkType.REMOTE]


def test_no_override_when_arg_is_none():
    """profiles are unchanged when args.query is None."""
    profiles = [_make_profile(query="keep me")]
    args = _make_args(query=None)
    apply_cli_overrides(profiles, args)
    assert profiles[0].query == "keep me"


def test_invalid_date_posted_exits():
    """Invalid --date-posted value causes sys.exit(1)."""
    profiles = [_make_profile()]
    args = _make_args(date_posted="invalid")
    with patch("builtins.print"):
        with pytest.raises(SystemExit) as exc_info:
            apply_cli_overrides(profiles, args)
    assert exc_info.value.code == 1


def test_invalid_scrapers_exits():
    """Invalid scraper name in --scrapers causes sys.exit(1)."""
    profiles = [_make_profile()]
    args = _make_args(scrapers="linkedin,monster")
    with patch("builtins.print"):
        with pytest.raises(SystemExit) as exc_info:
            apply_cli_overrides(profiles, args)
    assert exc_info.value.code == 1
