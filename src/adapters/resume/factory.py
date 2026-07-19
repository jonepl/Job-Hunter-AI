"""Factory for the resume parser adapter (ResumeParserPort)."""

from src.adapters.resume.pdf_parser import PyPDF2ResumeParser
from src.core.ports.resume_parser_port import ResumeParserPort


def build_resume_parser() -> ResumeParserPort:
    """Build the resume text-extraction adapter.

    Only PDF is supported today, so this returns a ``PyPDF2ResumeParser``. A future
    format would be selected here (e.g. by extension or an env flag) without any
    caller change.

    Returns:
        A ready ResumeParserPort implementation.
    """
    return PyPDF2ResumeParser()
