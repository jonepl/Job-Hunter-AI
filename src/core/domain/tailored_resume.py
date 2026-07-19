"""TailoredResume domain entity — the structured output of resume tailoring (F).

A generation LLM selects the candidate's *relevant* experience from the master
resume corpus (ADR-028) for one specific job and returns it as structured JSON,
not a text blob — so section order is a property of the renderer, never the model
(ADR-029). The deterministic formatter enforces the hard formatting rules over this
structure, and the ``.docx`` writer renders it. The content itself never leaves the
server (CLAUDE.md #2); only a file path and provenance do.
"""

from pydantic import BaseModel


class ResumeSection(BaseModel):
    """One heading-and-bullets block of a tailored resume (e.g. an experience entry)."""

    heading: str
    bullets: list[str] = []


class TailoredResume(BaseModel):
    """A resume tailored to a single job, as structured content ready to render."""

    summary: str
    sections: list[ResumeSection] = []
    skills: list[str] = []
