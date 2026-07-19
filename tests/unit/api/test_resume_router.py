"""Unit tests for the /api/resume router (W5).

Exercises the router in-process via FastAPI's TestClient against a real in-memory
SQLite resume repository plus a fake parser (returns fixed text, so no real PDF/
docx bytes are needed) — injected through a dependency override. No network, no
real files, consistent with the mock-all-externals rule.
"""

import io

from fastapi.testclient import TestClient

from src.adapters.repository.sqlite_resume_repository import SQLiteResumeRepository
from src.api.deps import get_resume_service
from src.api.main import create_app
from src.core.ports.resume_parser_port import ResumeParserPort
from src.core.services.resume_service import ResumeService


class _FakeParser(ResumeParserPort):
    """A parser that echoes a marker so ingest never touches PDF/docx internals."""

    def extract_text(self, data: bytes) -> str:
        """Return deterministic text derived from the byte length."""
        return f"Skills:\nPython, FastAPI\nSenior Engineer 2020 - 2024 ({len(data)}b)"


def _service(max_size_bytes: int = 5_000_000) -> ResumeService:
    """Build a ResumeService over an in-memory repo and the fake parser."""
    repo = SQLiteResumeRepository(db_path=":memory:")
    return ResumeService(_FakeParser(), repo, max_size_bytes=max_size_bytes)


def _client(service: ResumeService) -> TestClient:
    """Return a TestClient whose resume-service dependency is the given service."""
    app = create_app()
    app.dependency_overrides[get_resume_service] = lambda: service
    return TestClient(app)


def _upload(client: TestClient, data: bytes, filename: str = "resume.pdf"):
    """POST a file to /api/resume as multipart form data."""
    return client.post(
        "/api/resume",
        files={"file": (filename, io.BytesIO(data), "application/octet-stream")},
    )


def test_get_resume_empty_store_returns_null_active():
    """An empty store is a normal empty state, not a 404."""
    resp = _client(_service()).get("/api/resume")
    assert resp.status_code == 200
    assert resp.json() == {"active": None, "versions": []}


def test_upload_stores_and_returns_provenance_without_content():
    """A valid upload stores the version and returns provenance — never the text."""
    resp = _upload(_client(_service()), b"a valid resume payload", "avery.pdf")
    assert resp.status_code == 200
    body = resp.json()

    assert body["active"]["version"] == 1
    assert body["active"]["filename"] == "avery.pdf"
    assert body["active"]["isActive"] is True
    assert len(body["versions"]) == 1

    # The privacy boundary: resume content never leaves the API (ADR-028).
    assert "rawText" not in body["active"]
    assert "raw_text" not in body["active"]
    assert "contentHash" not in body["active"]


def test_upload_oversize_returns_400():
    """A file over the size ceiling fails clearly with a 400."""
    resp = _upload(_client(_service(max_size_bytes=10)), b"way too many bytes here")
    assert resp.status_code == 400
    assert "limit" in resp.json()["detail"].lower()


def test_upload_second_version_becomes_active():
    """Uploading different bytes creates v2 and makes it the active version."""
    client = _client(_service())
    _upload(client, b"first resume bytes")
    resp = _upload(client, b"second, different resume bytes")

    body = resp.json()
    assert body["active"]["version"] == 2
    assert len(body["versions"]) == 2
    # Newest-first ordering.
    assert [v["version"] for v in body["versions"]] == [2, 1]


def test_activate_earlier_version_flips_active():
    """Restoring an earlier version makes it active again."""
    client = _client(_service())
    _upload(client, b"first resume bytes")
    _upload(client, b"second, different resume bytes")

    resp = client.post("/api/resume/versions/1/activate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"]["version"] == 1
    assert next(v for v in body["versions"] if v["version"] == 1)["isActive"] is True
    assert next(v for v in body["versions"] if v["version"] == 2)["isActive"] is False


def test_activate_unknown_version_returns_404():
    """Restoring a version that does not exist yields a 404."""
    resp = _client(_service()).post("/api/resume/versions/99/activate")
    assert resp.status_code == 404
