"""Unit tests for the deterministic three-outcome document formatter (F, ADR-029).

The formatter is the heart of F, so it is tested as a table of raw→classified cases:
mechanical violations repaired, compound-word hyphens kept, and ambiguous hyphens
(dates/numbers) flagged for review but never rewritten.
"""

import pytest

from src.core.services.document_formatter import (
    TextSegment,
    _has_ambiguous_hyphen,
    format_segments,
)


def _one(text: str, location: str = "Summary"):
    """Format a single segment and return its FormatResult."""
    return format_segments([TextSegment(location=location, text=text)])


def test_clean_text_passes_through_unchanged():
    """Text with no violations is clean and untouched."""
    result = _one("Built reliable services with a small team.")
    assert result.outcome == "clean"
    assert result.segments[0].text == "Built reliable services with a small team."
    assert result.repair_note == ""
    assert result.review_locations == []


def test_semicolon_is_repaired_to_period():
    """A semicolon is a mechanical fix to a period; outcome is repaired."""
    result = _one("Shipped fast; stayed reliable")
    assert result.outcome == "repaired"
    assert ";" not in result.segments[0].text
    assert "semicolon to period" in result.repair_note


def test_em_dash_is_repaired_to_comma():
    """An em-dash is banned and mechanically replaced with a comma."""
    result = _one("Led the team — and shipped")
    assert result.outcome == "repaired"
    assert "—" not in result.segments[0].text
    assert "Led the team, and shipped" == result.segments[0].text
    assert "em-dash to comma" in result.repair_note


def test_leading_dash_bullet_marker_is_repaired():
    """A leading '- ' bullet marker becomes '• '."""
    result = _one("- Owned the migration")
    assert result.outcome == "repaired"
    assert result.segments[0].text == "• Owned the migration"
    assert "bullet marker to •" in result.repair_note


def test_leading_asterisk_bullet_marker_is_repaired():
    """A leading '* ' bullet marker becomes '• '."""
    result = _one("* Owned the migration")
    assert result.segments[0].text == "• Owned the migration"
    assert result.outcome == "repaired"


def test_compound_word_hyphen_is_kept_clean():
    """A letter-hyphen-letter compound word is allowed and left untouched."""
    result = _one("Senior full-stack engineer, well-documented work")
    assert result.outcome == "clean"
    assert result.segments[0].text == "Senior full-stack engineer, well-documented work"


def test_year_range_hyphen_is_flagged_not_rewritten():
    """A date range like 2020-2024 is flagged for review and never rewritten."""
    result = _one("Acme Corp, 2020-2024")
    assert result.outcome == "needs_review"
    assert "2020-2024" in result.segments[0].text  # digits never altered
    assert "[PLACEHOLDER: review]" in result.segments[0].text
    assert result.review_locations == ["Summary"]


def test_spaced_hyphen_around_number_is_flagged():
    """A spaced separator hyphen near a number is flagged, not guessed."""
    result = _one("Python - 5 years", location="Skills → item 1")
    assert result.outcome == "needs_review"
    assert "Python - 5 years" in result.segments[0].text
    assert result.review_locations == ["Skills → item 1"]


def test_mixed_mechanical_and_semantic_is_needs_review():
    """When both a mechanical fix and a flag occur, needs_review wins the outcome."""
    result = format_segments(
        [
            TextSegment(location="Summary", text="Fast; effective"),
            TextSegment(location="Experience → bullet 1", text="Grew 2019-2023"),
        ]
    )
    assert result.outcome == "needs_review"
    # The mechanical repair still happened on the clean segment.
    assert result.segments[0].text == "Fast. effective"
    assert "semicolon to period" in result.repair_note
    # Only the ambiguous segment is listed for review.
    assert result.review_locations == ["Experience → bullet 1"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("full-stack", False),
        ("well-documented and API-first", False),
        ("2020-2024", True),
        ("5-10 years", True),
        ("Python - 5 years", True),
        ("no hyphen here", False),
    ],
)
def test_has_ambiguous_hyphen_table(text, expected):
    """Compound-word hyphens are clean; every other hyphen is ambiguous."""
    assert _has_ambiguous_hyphen(text) is expected
