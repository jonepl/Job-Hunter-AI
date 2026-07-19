"""Unit tests for src/bootstrap.py — DB-backed profile loading (W7)."""

from unittest.mock import MagicMock, patch

import pytest

from src.bootstrap import load_profiles


def test_load_profiles_returns_profiles_from_the_store():
    """load_profiles() returns the profiles the SettingsService lists."""
    mock_profiles = [object(), object()]
    service = MagicMock()
    service.list_profiles.return_value = mock_profiles
    with patch("src.bootstrap.build_settings_service", return_value=service):
        result = load_profiles()
    assert result is mock_profiles


def test_load_profiles_exits_when_no_profiles_configured():
    """load_profiles() calls sys.exit(1) when the store is empty."""
    service = MagicMock()
    service.list_profiles.return_value = []
    with patch("src.bootstrap.build_settings_service", return_value=service), \
         patch("builtins.print"):
        with pytest.raises(SystemExit) as exc_info:
            load_profiles()
    assert exc_info.value.code == 1
