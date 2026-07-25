"""Unit tests for DocxWriter — the one real-file test (write + reopen).

python-docx is a local library and these write to a temp dir, so a genuine
round-trip (write then reopen and read) is allowed and is the surest proof the
writer produces a valid ``.docx``.
"""

from docx import Document

from src.adapters.generation.docx_writer import DocxWriter
from src.core.domain.cover_letter import CoverLetter
from src.core.domain.tailored_resume import ResumeSection, TailoredResume


def _paragraph_texts(path: str) -> list[str]:
    """Reopen the .docx at ``path`` and return its paragraph texts."""
    return [p.text for p in Document(path).paragraphs]


def test_write_resume_produces_a_valid_docx(tmp_path):
    """A tailored resume is written as a reopenable .docx with bulleted content."""
    path = str(tmp_path / "resume.docx")
    doc = TailoredResume(
        summary="Senior engineer.",
        sections=[ResumeSection(heading="Experience", bullets=["Shipped a system."])],
        skills=["Python", "SQL"],
    )
    DocxWriter().write_resume(doc, path)

    texts = _paragraph_texts(path)
    assert "Senior engineer." in texts
    assert "Python, SQL" in texts
    assert "• Shipped a system." in texts


def test_write_resume_normalizes_a_stray_bullet_marker(tmp_path):
    """A bullet already carrying a marker is rendered with exactly one '•'."""
    path = str(tmp_path / "r.docx")
    doc = TailoredResume(summary="s", sections=[ResumeSection(heading="X", bullets=["• Did it"])])
    DocxWriter().write_resume(doc, path)
    assert "• Did it" in _paragraph_texts(path)
    assert "• • Did it" not in _paragraph_texts(path)


def test_write_cover_letter_produces_a_valid_docx(tmp_path):
    """A cover letter is written as a reopenable .docx with its paragraphs."""
    path = str(tmp_path / "letter.docx")
    letter = CoverLetter(
        salutation="Dear Team,",
        paragraphs=["I am a strong fit.", "I would love to help."],
        closing="Sincerely, Jane",
    )
    DocxWriter().write_cover_letter(letter, path)

    texts = _paragraph_texts(path)
    assert "Dear Team," in texts
    assert "I am a strong fit." in texts
    assert "Sincerely, Jane" in texts


def test_write_creates_missing_parent_directory(tmp_path):
    """The writer creates the destination directory if it does not exist."""
    path = str(tmp_path / "nested" / "deep" / "resume.docx")
    DocxWriter().write_resume(TailoredResume(summary="s"), path)
    assert _paragraph_texts(path)  # file exists and is readable
