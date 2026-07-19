"""PyPDF2ResumeParser — extract resume text from PDF bytes (ResumeParserPort).

Lifts the PDF extraction that previously lived inline in ``JobSearchService``
behind the ``ResumeParserPort`` so the core no longer imports PyPDF2 directly and
the same logic serves both a filesystem path (CLI, auto-seed) and uploaded bytes
(the future ``POST /resume``, W5).
"""

import io

import PyPDF2

from src.core.ports.resume_parser_port import ResumeParserPort


class PyPDF2ResumeParser(ResumeParserPort):
    """Extract plain text from a PDF resume using PyPDF2."""

    def extract_text(self, data: bytes) -> str:
        """Extract whitespace-stripped text from the given PDF bytes.

        Args:
            data: The raw PDF file contents.

        Returns:
            The concatenated, stripped page text.

        Raises:
            ValueError: When the PDF yields no extractable text.
        """
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        raw_text = "\n".join(pages).strip()

        if not raw_text:
            raise ValueError("No text could be extracted from the resume PDF")

        return raw_text
