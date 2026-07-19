"""Unit tests for PyPDF2ResumeParser (PyPDF2 mocked — no real PDF I/O)."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.resume.pdf_parser import PyPDF2ResumeParser


def _reader_with_pages(*texts: str) -> MagicMock:
    """Return a fake PdfReader whose pages extract the given texts."""
    reader = MagicMock()
    reader.pages = [MagicMock(extract_text=MagicMock(return_value=t)) for t in texts]
    return reader


@patch("src.adapters.resume.pdf_parser.PyPDF2.PdfReader")
def test_extract_text_joins_and_strips_pages(mock_reader_cls):
    """Page texts are joined with newlines and surrounding whitespace stripped."""
    mock_reader_cls.return_value = _reader_with_pages("  Alpha ", "Beta  ")
    text = PyPDF2ResumeParser().extract_text(b"%PDF-fake")
    assert text == "Alpha \nBeta"


@patch("src.adapters.resume.pdf_parser.PyPDF2.PdfReader")
def test_extract_text_tolerates_none_page_text(mock_reader_cls):
    """A page returning None contributes an empty string, not a crash."""
    reader = MagicMock()
    reader.pages = [MagicMock(extract_text=MagicMock(return_value=None)),
                    MagicMock(extract_text=MagicMock(return_value="Real"))]
    mock_reader_cls.return_value = reader
    assert PyPDF2ResumeParser().extract_text(b"%PDF-fake") == "Real"


@patch("src.adapters.resume.pdf_parser.PyPDF2.PdfReader")
def test_extract_text_empty_pdf_raises_value_error(mock_reader_cls):
    """A PDF that yields no text raises ValueError (unchanged legacy behavior)."""
    mock_reader_cls.return_value = _reader_with_pages("", "   ")
    with pytest.raises(ValueError, match="No text could be extracted"):
        PyPDF2ResumeParser().extract_text(b"%PDF-fake")
