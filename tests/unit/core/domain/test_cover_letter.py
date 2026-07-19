"""Unit tests for the CoverLetter domain entity."""

from src.core.domain.cover_letter import CoverLetter


def test_cover_letter_holds_salutation_paragraphs_closing():
    """A cover letter is a salutation, body paragraphs, and a closing."""
    letter = CoverLetter(
        salutation="Dear Hiring Team,",
        paragraphs=["First paragraph.", "Second paragraph."],
        closing="Sincerely, Jane",
    )
    assert letter.salutation == "Dear Hiring Team,"
    assert len(letter.paragraphs) == 2
    assert letter.closing == "Sincerely, Jane"


def test_cover_letter_defaults_no_paragraphs():
    """Paragraphs default to an empty list."""
    letter = CoverLetter(salutation="Hi,", closing="Thanks")
    assert letter.paragraphs == []
