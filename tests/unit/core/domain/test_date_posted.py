"""Unit tests for the DatePosted domain type."""

import pytest

from src.core.domain.date_posted import DatePosted

# ---------------------------------------------------------------------------
# from_string — valid values
# ---------------------------------------------------------------------------


def test_from_string_24h():
    """'24h' parses to DatePosted.DAY."""
    assert DatePosted.from_string("24h") == DatePosted.DAY


def test_from_string_3days():
    """'3days' parses to DatePosted.DAYS3."""
    assert DatePosted.from_string("3days") == DatePosted.DAYS3


def test_from_string_week():
    """'week' parses to DatePosted.WEEK."""
    assert DatePosted.from_string("week") == DatePosted.WEEK


def test_from_string_month():
    """'month' parses to DatePosted.MONTH."""
    assert DatePosted.from_string("month") == DatePosted.MONTH


# ---------------------------------------------------------------------------
# from_string — case insensitivity and whitespace
# ---------------------------------------------------------------------------


def test_from_string_case_insensitive_week():
    """'Week' (mixed case) parses to DatePosted.WEEK."""
    assert DatePosted.from_string("Week") == DatePosted.WEEK


def test_from_string_case_insensitive_month():
    """'MONTH' (upper case) parses to DatePosted.MONTH."""
    assert DatePosted.from_string("MONTH") == DatePosted.MONTH


def test_from_string_strips_whitespace():
    """' 3days ' (leading/trailing spaces) parses to DatePosted.DAYS3."""
    assert DatePosted.from_string(" 3days ") == DatePosted.DAYS3


# ---------------------------------------------------------------------------
# from_string — invalid value
# ---------------------------------------------------------------------------


def test_from_string_raises_on_invalid():
    """Unrecognised value raises ValueError with supported values in the message."""
    with pytest.raises(ValueError) as exc_info:
        DatePosted.from_string("yesterday")
    message = str(exc_info.value)
    assert "24h, 3days, week, month" in message


# ---------------------------------------------------------------------------
# linkedin_param
# ---------------------------------------------------------------------------


def test_linkedin_param_24h():
    """DAY.linkedin_param returns 'r86400'."""
    assert DatePosted.DAY.linkedin_param == "r86400"


def test_linkedin_param_3days():
    """DAYS3.linkedin_param returns 'r259200'."""
    assert DatePosted.DAYS3.linkedin_param == "r259200"


def test_linkedin_param_week():
    """WEEK.linkedin_param returns 'r604800'."""
    assert DatePosted.WEEK.linkedin_param == "r604800"


def test_linkedin_param_month():
    """MONTH.linkedin_param returns 'r2592000'."""
    assert DatePosted.MONTH.linkedin_param == "r2592000"


# ---------------------------------------------------------------------------
# jsearch_param
# ---------------------------------------------------------------------------


def test_jsearch_param_24h():
    """DAY.jsearch_param returns 'today'."""
    assert DatePosted.DAY.jsearch_param == "today"


def test_jsearch_param_3days():
    """DAYS3.jsearch_param returns '3days'."""
    assert DatePosted.DAYS3.jsearch_param == "3days"


def test_jsearch_param_week():
    """WEEK.jsearch_param returns 'week'."""
    assert DatePosted.WEEK.jsearch_param == "week"


def test_jsearch_param_month():
    """MONTH.jsearch_param returns 'month'."""
    assert DatePosted.MONTH.jsearch_param == "month"
