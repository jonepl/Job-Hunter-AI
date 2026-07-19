"""Unit tests for ResumeService.

Uses the real in-memory SQLiteResumeRepository (our own store) plus a stub parser
whose extraction is controlled per test — no real PDF I/O or network.
"""

import pytest

from src.adapters.repository.sqlite_resume_repository import SQLiteResumeRepository
from src.core.ports.resume_parser_port import ResumeParserPort
from src.core.services.resume_service import ResumeService


class _StubParser(ResumeParserPort):
    """A parser that returns a fixed text and records how often it was called."""

    def __init__(self, text: str = "Extracted resume text") -> None:
        self.text = text
        self.calls = 0

    def extract_text(self, data: bytes) -> str:
        self.calls += 1
        return self.text


def _service(parser: ResumeParserPort | None = None, max_size_bytes: int = 5_000_000):
    """Return a ResumeService over a fresh in-memory store."""
    parser = parser or _StubParser()
    repo = SQLiteResumeRepository(db_path=":memory:")
    return ResumeService(parser, repo, max_size_bytes=max_size_bytes), parser, repo


def test_ingest_parses_stores_and_activates_v1():
    """First ingest parses once, stores v1, and marks it active."""
    service, parser, _ = _service(_StubParser("Senior Engineer resume corpus"))
    stored = service.ingest(b"%PDF-a", "resume.pdf")

    assert stored.version == 1
    assert stored.is_active is True
    assert stored.filename == "resume.pdf"
    assert stored.raw_text == "Senior Engineer resume corpus"
    assert stored.size_bytes == len(b"%PDF-a")
    assert stored.content_hash  # a hash was recorded
    assert parser.calls == 1


def test_ingest_identical_bytes_reactivates_without_reparsing():
    """Re-uploading identical bytes reuses the version — no re-parse, no duplicate."""
    service, parser, repo = _service()
    first = service.ingest(b"%PDF-same", "resume.pdf")
    again = service.ingest(b"%PDF-same", "resume-renamed.pdf")

    assert again.version == first.version
    assert parser.calls == 1  # not parsed a second time
    assert len(repo.list_versions()) == 1


def test_ingest_different_bytes_creates_v2_active():
    """Different bytes are parsed and stored as a new active version."""
    service, parser, repo = _service()
    service.ingest(b"%PDF-a", "a.pdf")
    v2 = service.ingest(b"%PDF-b", "b.pdf")

    assert v2.version == 2
    assert v2.is_active is True
    assert parser.calls == 2
    assert len(repo.list_versions()) == 2


def test_ingest_rejects_oversized_file():
    """A file over the size ceiling raises before any parse or store."""
    service, parser, repo = _service(max_size_bytes=4)
    with pytest.raises(ValueError, match="over the"):
        service.ingest(b"too-large-payload", "big.pdf")
    assert parser.calls == 0
    assert repo.get_active() is None


def test_ingest_path_reads_bytes_and_uses_basename(tmp_path):
    """ingest_path reads the file and records its basename as the filename."""
    service, _, _ = _service(_StubParser("corpus from disk"))
    pdf = tmp_path / "my_resume.pdf"
    pdf.write_bytes(b"%PDF-disk")

    stored = service.ingest_path(str(pdf))
    assert stored.filename == "my_resume.pdf"
    assert stored.raw_text == "corpus from disk"


def test_estimate_counts_from_skills_section_and_date_ranges():
    """Skill/role counts are estimated from a skills section and date ranges."""
    text = (
        "EXPERIENCE\n"
        "Acme Corp 2020 - 2024\n"
        "Globex 2016 – 2020\n"
        "\n"
        "Skills\n"
        "Python, FastAPI, SQL | Docker\n"
    )
    service, _, _ = _service(_StubParser(text))
    stored = service.ingest(b"%PDF-counts", "r.pdf")

    assert stored.skill_count == 4  # Python, FastAPI, SQL, Docker
    assert stored.role_count == 2   # two date ranges


def test_get_active_and_list_and_activate_pass_through():
    """get_active/list_versions/activate reflect the underlying store."""
    service, _, _ = _service()
    assert service.get_active() is None
    service.ingest(b"%PDF-a", "a.pdf")
    service.ingest(b"%PDF-b", "b.pdf")

    assert service.get_active().version == 2
    assert [r.version for r in service.list_versions()] == [2, 1]
    assert service.activate(1) is True
    assert service.get_active().version == 1
    assert service.activate(99) is False
