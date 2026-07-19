"""ResumeParserPort — abstract interface for extracting text from a resume file.

Keeps the concrete PDF library out of the core (ADR-003): the core sees only
this port, and adapters (``PyPDF2ResumeParser`` today) provide the extraction.
The port trades in raw bytes so it serves both a filesystem path (the CLI and
auto-seed) and an uploaded byte stream (the future ``POST /resume``, W5).
"""

from abc import ABC, abstractmethod


class ResumeParserPort(ABC):
    """Abstract base class for resume text-extraction adapters."""

    @abstractmethod
    def extract_text(self, data: bytes) -> str:
        """Extract plain text from the raw bytes of a resume document.

        Args:
            data: The raw file bytes (e.g. a PDF's contents).

        Returns:
            The extracted, whitespace-stripped text corpus.

        Raises:
            ValueError: When no text can be extracted from the document.
        """
        ...
