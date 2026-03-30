"""Unit tests for CLI argument parsing and location resolution in main.py."""

import sys
from unittest.mock import patch

import pytest

from src.main import _parse_args, _resolve_location


def test_location_defaults_to_united_states_for_remote():
    """Remote only, no --location → resolved location is 'United States'."""
    with patch("sys.argv", ["prog", "--query", "SE", "--work-type", "remote"]):
        args = _parse_args()
    location, defaulted = _resolve_location(args)
    assert location == "United States"
    assert defaulted is True


def test_location_used_as_provided_for_remote():
    """Remote only, --location provided → resolved location is the provided value."""
    with patch("sys.argv", ["prog", "--query", "SE", "--location", "New York", "--work-type", "remote"]):
        args = _parse_args()
    location, defaulted = _resolve_location(args)
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
    location, defaulted = _resolve_location(args)
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
    location, defaulted = _resolve_location(args)
    assert location == "New York"
    assert defaulted is False
