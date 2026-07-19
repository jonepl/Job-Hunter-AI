"""Unit tests for the TailoredResume domain entity."""

from src.core.domain.tailored_resume import ResumeSection, TailoredResume


def test_tailored_resume_defaults_empty_collections():
    """A summary alone is valid; sections and skills default to empty lists."""
    doc = TailoredResume(summary="A concise summary.")
    assert doc.sections == []
    assert doc.skills == []


def test_tailored_resume_holds_sections_and_skills():
    """Sections carry a heading and bullets; skills are a flat list."""
    doc = TailoredResume(
        summary="Summary.",
        sections=[ResumeSection(heading="Experience", bullets=["Did a thing."])],
        skills=["Python", "SQL"],
    )
    assert doc.sections[0].heading == "Experience"
    assert doc.sections[0].bullets == ["Did a thing."]
    assert doc.skills == ["Python", "SQL"]


def test_resume_section_defaults_no_bullets():
    """A section may have a heading with no bullets."""
    section = ResumeSection(heading="Education")
    assert section.bullets == []
