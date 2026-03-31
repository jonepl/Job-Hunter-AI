"""Unit tests for src/bootstrap.py — profile loading."""

from unittest.mock import patch

import pytest

from src.bootstrap import load_profiles


def test_load_profiles_returns_profiles():
    """load_profiles() returns profiles from SearchProfile.load_all()."""
    mock_profiles = [object(), object()]
    with patch("src.bootstrap.SearchProfile.load_all", return_value=mock_profiles):
        result = load_profiles()
    assert result is mock_profiles


def test_load_profiles_exits_on_value_error():
    """load_profiles() calls sys.exit(1) when SearchProfile.load_all() raises ValueError."""
    with patch("src.bootstrap.SearchProfile.load_all", side_effect=ValueError("bad config")), \
         patch("builtins.print"):
        with pytest.raises(SystemExit) as exc_info:
            load_profiles()
    assert exc_info.value.code == 1
