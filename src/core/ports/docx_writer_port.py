"""DocxWriterPort — abstract interface for rendering documents to ``.docx`` (F).

``OutputPort``'s ``deliver(report)`` contract is the wrong shape for a
user-triggered single artifact, so generation gets its own writer port (ADR-029).
ADR-029 named a ``TailoredResumeWriterPort`` when the resume and cover-letter
stories were separate; the merged **F** consolidates both into this one docx-writer
port serving both artifact types (the merge is recorded in §15 gap 4/7 — no new
ADR). Keeping python-docx behind a port keeps the rendering library out of the core.
"""

from abc import ABC, abstractmethod

from src.core.domain.cover_letter import CoverLetter
from src.core.domain.tailored_resume import TailoredResume


class DocxWriterPort(ABC):
    """Abstract base class defining the ``.docx`` rendering contract."""

    @abstractmethod
    def write_resume(self, doc: TailoredResume, path: str) -> None:
        """Render a tailored resume to a ``.docx`` file at ``path``.

        Args:
            doc: The structured tailored resume to render.
            path: Destination file path (parent directories are created).
        """
        ...

    @abstractmethod
    def write_cover_letter(self, doc: CoverLetter, path: str) -> None:
        """Render a cover letter to a ``.docx`` file at ``path``.

        Args:
            doc: The structured cover letter to render.
            path: Destination file path (parent directories are created).
        """
        ...
