"""Unit tests for src/resume_runner.py — the ``resume`` CLI backend.

Exercised against a real ResumeService over an in-memory store with a stub parser
— no real PDF I/O or network.
"""

from src.adapters.repository.sqlite_resume_repository import SQLiteResumeRepository
from src.core.ports.resume_parser_port import ResumeParserPort
from src.core.services.resume_service import ResumeService
from src.orchestration.resume_runner import (
    run_resume_activate,
    run_resume_list,
    run_resume_upload,
)


class _StubParser(ResumeParserPort):
    """A parser returning a fixed text."""

    def extract_text(self, data: bytes) -> str:
        return "Senior Engineer corpus"


def _service() -> ResumeService:
    """Return a ResumeService over a fresh in-memory store."""
    return ResumeService(_StubParser(), SQLiteResumeRepository(db_path=":memory:"))


def _write_pdf(tmp_path, name: str = "resume.pdf", data: bytes = b"%PDF-a"):
    """Write a fake PDF file and return its path."""
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def test_upload_stores_and_reports_version(tmp_path):
    """Uploading a new file stores v1 and returns a success message + exit 0."""
    service = _service()
    message, code = run_resume_upload(service, _write_pdf(tmp_path))

    assert code == 0
    assert "v1" in message
    assert service.get_active().version == 1


def test_upload_missing_file_returns_exit_1(tmp_path):
    """A missing path is a clean error, not a traceback."""
    service = _service()
    message, code = run_resume_upload(service, str(tmp_path / "nope.pdf"))

    assert code == 1
    assert "No resume file" in message


def test_upload_oversized_file_returns_exit_1(tmp_path):
    """A file over the size ceiling reports a clear error and exit 1."""
    service = ResumeService(
        _StubParser(), SQLiteResumeRepository(db_path=":memory:"), max_size_bytes=4
    )
    message, code = run_resume_upload(service, _write_pdf(tmp_path, data=b"way-too-big"))

    assert code == 1
    assert "Could not store resume" in message


def test_list_empty_store(tmp_path):
    """Listing an empty store is a valid, non-error state."""
    message, code = run_resume_list(_service())

    assert code == 0
    assert "No master resume stored" in message


def test_list_marks_active_version(tmp_path):
    """Listing shows every version and marks the active one."""
    service = _service()
    run_resume_upload(service, _write_pdf(tmp_path, "a.pdf", b"%PDF-a"))
    run_resume_upload(service, _write_pdf(tmp_path, "b.pdf", b"%PDF-b"))

    message, code = run_resume_list(service)

    assert code == 0
    assert "v2" in message and "v1" in message
    # The active (v2) line carries the active marker.
    active_line = next(line for line in message.splitlines() if "v2" in line)
    assert active_line.startswith("* ")


def test_activate_restores_prior_version(tmp_path):
    """Activating an existing version restores it and returns exit 0."""
    service = _service()
    run_resume_upload(service, _write_pdf(tmp_path, "a.pdf", b"%PDF-a"))
    run_resume_upload(service, _write_pdf(tmp_path, "b.pdf", b"%PDF-b"))

    message, code = run_resume_activate(service, 1)

    assert code == 0
    assert "v1 is now active" in message
    assert service.get_active().version == 1


def test_activate_missing_version_returns_exit_1(tmp_path):
    """Activating a non-existent version is a clean error with exit 1."""
    service = _service()
    run_resume_upload(service, _write_pdf(tmp_path))

    message, code = run_resume_activate(service, 99)

    assert code == 1
    assert "No stored resume version 99" in message
