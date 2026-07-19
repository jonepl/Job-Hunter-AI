"""Factory for the resume parser adapter (ResumeParserPort)."""

from src.adapters.resume.docx_parser import DocxResumeParser
from src.adapters.resume.format_router import ResumeFormatRouter
from src.adapters.resume.pdf_parser import PyPDF2ResumeParser
from src.core.ports.resume_parser_port import ResumeParserPort


def build_resume_parser() -> ResumeParserPort:
    """Build the resume text-extraction adapter.

    Both ``.pdf`` and ``.docx`` are supported (W5), so this returns a
    ``ResumeFormatRouter`` that sniffs the uploaded bytes and delegates to the
    matching format parser. A future format would be added as another parser
    wired into the router, without any caller change.

    Returns:
        A ready ResumeParserPort implementation.
    """
    return ResumeFormatRouter(PyPDF2ResumeParser(), DocxResumeParser())
