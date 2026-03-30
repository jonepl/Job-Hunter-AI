"""Unit tests for the ScraperName domain enum."""

import pytest

from src.core.domain.scraper_name import ScraperName


# ---------------------------------------------------------------------------
# from_string — happy path
# ---------------------------------------------------------------------------

def test_from_string_linkedin():
    """'linkedin' parses to ScraperName.LINKEDIN."""
    assert ScraperName.from_string("linkedin") == ScraperName.LINKEDIN


def test_from_string_indeed():
    """'indeed' parses to ScraperName.INDEED."""
    assert ScraperName.from_string("indeed") == ScraperName.INDEED


def test_from_string_glassdoor():
    """'glassdoor' parses to ScraperName.GLASSDOOR."""
    assert ScraperName.from_string("glassdoor") == ScraperName.GLASSDOOR


def test_from_string_ziprecruiter():
    """'ziprecruiter' parses to ScraperName.ZIPRECRUITER."""
    assert ScraperName.from_string("ziprecruiter") == ScraperName.ZIPRECRUITER


def test_from_string_case_insensitive():
    """from_string() is case insensitive."""
    assert ScraperName.from_string("LinkedIn") == ScraperName.LINKEDIN
    assert ScraperName.from_string("INDEED") == ScraperName.INDEED


def test_from_string_strips_whitespace():
    """from_string() strips leading and trailing whitespace."""
    assert ScraperName.from_string(" linkedin ") == ScraperName.LINKEDIN


def test_from_string_raises_on_invalid():
    """from_string() raises ValueError with helpful message for unknown names."""
    with pytest.raises(ValueError) as exc_info:
        ScraperName.from_string("monster")
    message = str(exc_info.value)
    assert "linkedin" in message
    assert "indeed" in message
    assert "glassdoor" in message
    assert "ziprecruiter" in message


# ---------------------------------------------------------------------------
# parse_list
# ---------------------------------------------------------------------------

def test_parse_list_single():
    """Single-item comma string parses to one ScraperName."""
    assert ScraperName.parse_list("linkedin") == [ScraperName.LINKEDIN]


def test_parse_list_multiple():
    """Two-item comma string parses to two ScraperNames in order."""
    result = ScraperName.parse_list("linkedin,indeed")
    assert result == [ScraperName.LINKEDIN, ScraperName.INDEED]


def test_parse_list_with_spaces():
    """parse_list() strips whitespace around each name."""
    result = ScraperName.parse_list("linkedin, indeed, glassdoor")
    assert result == [
        ScraperName.LINKEDIN,
        ScraperName.INDEED,
        ScraperName.GLASSDOOR,
    ]


def test_parse_list_raises_on_invalid_name():
    """parse_list() raises ValueError when any name in the list is invalid."""
    with pytest.raises(ValueError):
        ScraperName.parse_list("linkedin,monster")


# ---------------------------------------------------------------------------
# all
# ---------------------------------------------------------------------------

def test_all_returns_all_four():
    """ScraperName.all() returns all four ScraperName values."""
    result = ScraperName.all()
    assert len(result) == 4
    assert ScraperName.LINKEDIN in result
    assert ScraperName.INDEED in result
    assert ScraperName.GLASSDOOR in result
    assert ScraperName.ZIPRECRUITER in result
