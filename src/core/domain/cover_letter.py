"""CoverLetter domain entity — the structured output of cover-letter generation (F).

The generation LLM returns a salutation, body paragraphs, and a closing as
structured JSON (ADR-029), written in the candidate's voice (a structured
descriptor, not writing samples — ADR-030). The deterministic formatter enforces
the hard formatting rules and the ``.docx`` writer renders it. As with the tailored
resume, the content never leaves the server (CLAUDE.md #2).
"""

from pydantic import BaseModel


class CoverLetter(BaseModel):
    """A cover letter tailored to a single job, as structured content to render."""

    salutation: str
    paragraphs: list[str] = []
    closing: str
