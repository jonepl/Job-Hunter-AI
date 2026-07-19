"""Unit tests for ResumeFormatRouter — magic-byte format dispatch."""

from unittest.mock import MagicMock

import pytest

from src.adapters.resume.format_router import ResumeFormatRouter


def _router() -> tuple[ResumeFormatRouter, MagicMock, MagicMock]:
    """Return a router wired to two fake parsers, plus the fakes."""
    pdf = MagicMock()
    pdf.extract_text.return_value = "pdf text"
    docx = MagicMock()
    docx.extract_text.return_value = "docx text"
    return ResumeFormatRouter(pdf, docx), pdf, docx


def test_pdf_magic_routes_to_pdf_parser():
    """Bytes starting with %PDF go to the PDF parser."""
    router, pdf, docx = _router()
    data = b"%PDF-1.7 rest"
    assert router.extract_text(data) == "pdf text"
    pdf.extract_text.assert_called_once_with(data)
    docx.extract_text.assert_not_called()


def test_zip_magic_routes_to_docx_parser():
    """Bytes starting with the ZIP header (a .docx) go to the DOCX parser."""
    router, pdf, docx = _router()
    data = b"PK\x03\x04 rest of a docx"
    assert router.extract_text(data) == "docx text"
    docx.extract_text.assert_called_once_with(data)
    pdf.extract_text.assert_not_called()


def test_unknown_magic_raises_value_error():
    """Neither PDF nor ZIP magic raises a clear ValueError; no parser is called."""
    router, pdf, docx = _router()
    with pytest.raises(ValueError, match="Unsupported resume format"):
        router.extract_text(b"plain text resume")
    pdf.extract_text.assert_not_called()
    docx.extract_text.assert_not_called()
