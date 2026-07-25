"""Unit tests for the /api generations router (W6).

Drives the async generation endpoints in-process via FastAPI's TestClient against a
real ``GenerationService`` wired to in-memory repositories and fake tailor/cover/
writer ports (no LLM, no network). Starlette's TestClient runs the post-response
``BackgroundTasks`` before the request call returns, so a ``POST`` immediately
followed by a poll observes the completed row.
"""

import os
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from src.adapters.repository.sqlite_generation_repository import (
    SQLiteGenerationRepository,
)
from src.api.deps import get_generation_service
from src.api.main import create_app
from src.core.domain.cover_letter import CoverLetter
from src.core.domain.generation import Generation
from src.core.domain.resume import Resume
from src.core.domain.stored_job import StoredJob
from src.core.domain.tailored_resume import TailoredResume
from src.core.ports.cover_letter_port import CoverLetterPort
from src.core.ports.docx_writer_port import DocxWriterPort
from src.core.ports.resume_tailor_port import ResumeTailorPort
from src.core.services.generation_service import GenerationService

_NOW = datetime(2026, 7, 18, 9, 0, 0)


class _FakeTailor(ResumeTailorPort):
    """A tailor returning a fixed clean resume (or raising to simulate failure)."""

    def __init__(self, fail: bool = False) -> None:
        self.provider = "openai"
        self.model = "gpt-4o"
        self._fail = fail

    async def tailor(self, resume, job, feedback=None):
        if self._fail:
            raise RuntimeError("SECRETMODELOUTPUT provider exploded")
        return TailoredResume(summary="A clean tailored summary.")


class _FakeCoverLetter(CoverLetterPort):
    """A cover-letter adapter returning a fixed clean letter."""

    def __init__(self) -> None:
        self.provider = "anthropic"
        self.model = "claude-sonnet-4-5"

    async def generate(self, resume, job, voice, feedback=None):
        return CoverLetter(salutation="Hi,", paragraphs=["A good fit."], closing="Bye")


class _RealFileWriter(DocxWriterPort):
    """A writer that writes a tiny real file so the download route can stat/stream it."""

    def write_resume(self, resume, path: str) -> None:
        self._write(path)

    def write_cover_letter(self, letter, path: str) -> None:
        self._write(path)

    @staticmethod
    def _write(path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(b"PK\x03\x04 fake docx bytes")


class _FakeResumeService:
    """Exposes only get_active, as GenerationService uses."""

    def __init__(self, resume: Resume | None) -> None:
        self._resume = resume

    def get_active(self) -> Resume | None:
        return self._resume


class _FakeJobRepo:
    """Exposes only get_job — returns a stored job for id 7, else None."""

    def get_job(self, job_id: int) -> StoredJob | None:
        if job_id != 7:
            return None
        return StoredJob(
            id=7,
            company="Acme",
            title="Staff Engineer",
            location="Remote",
            url="https://x/1",
            description="Build things.",
            fingerprint="acme|staff|remote",
            fingerprint_version=1,
            canon_company="acme",
            canon_title="staff engineer",
            canon_location="remote",
            first_seen_at=_NOW,
            last_seen_at=_NOW,
            seen_on=["linkedin"],
        )


def _service(
    tmp_path,
    *,
    resume: bool = True,
    fail: bool = False,
    timeout: float = 120.0,
) -> GenerationService:
    """Build a GenerationService over in-memory repos + fakes, writing to tmp_path."""
    active = Resume(raw_text="Backend corpus.", parsed_at=_NOW, is_active=True) if resume else None
    repo = SQLiteGenerationRepository(db_path=":memory:")
    _seed_job(repo, 7)  # generations.job_id has a FK to jobs
    return GenerationService(
        tailor=_FakeTailor(fail=fail),
        cover_letter=_FakeCoverLetter(),
        writer=_RealFileWriter(),
        generation_repo=repo,
        resume_service=_FakeResumeService(active),
        job_repository=_FakeJobRepo(),
        generations_dir=str(tmp_path / "generations"),
        generation_timeout_seconds=timeout,
    )


def _seed_job(repo: SQLiteGenerationRepository, job_id: int) -> None:
    """Insert a minimal jobs row so a generation can reference it (FK constraint)."""
    repo._conn.execute(
        "INSERT INTO jobs ("
        "id, fingerprint_version, canon_company, canon_title, canon_location, "
        "company, title, location, first_seen_at, last_seen_at"
        ") VALUES (?, 1, 'c', 't', 'l', 'Co', 'Title', 'Loc', ?, ?)",
        (job_id, _NOW.isoformat(), _NOW.isoformat()),
    )
    repo._conn.commit()


def _client(service: GenerationService) -> TestClient:
    """Return a TestClient whose generation-service dependency is the given service."""
    app = create_app()
    app.dependency_overrides[get_generation_service] = lambda: service
    return TestClient(app)


def test_generate_returns_202_pending_without_content(tmp_path):
    """POST starts generation, returns 202 + a pending record with no file path."""
    resp = _client(_service(tmp_path)).post("/api/jobs/7/generate", json={"kind": "resume"})
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] in ("pending", "ready")  # background task may already be done
    assert body["kind"] == "resume"
    assert body["jobId"] == 7
    assert "filePath" not in body and "file_path" not in body


def test_generate_then_poll_reaches_ready(tmp_path):
    """The background task completes, and the poll reports a ready/clean generation."""
    client = _client(_service(tmp_path))
    gen_id = client.post("/api/jobs/7/generate", json={"kind": "resume"}).json()["id"]

    resp = client.get(f"/api/generations/{gen_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["outcome"] == "clean"


def test_generate_with_no_resume_returns_400(tmp_path):
    """Generating with no stored master resume is a clear 400, not a failed job."""
    resp = _client(_service(tmp_path, resume=False)).post(
        "/api/jobs/7/generate", json={"kind": "resume"}
    )
    assert resp.status_code == 400
    assert "resume" in resp.json()["detail"].lower()


def test_generate_unknown_job_returns_400(tmp_path):
    """Generating for an unknown job id is a clear 400."""
    resp = _client(_service(tmp_path)).post("/api/jobs/999/generate", json={"kind": "resume"})
    assert resp.status_code == 400


def test_failed_generation_reports_failed_and_leaks_nothing(tmp_path):
    """A provider error surfaces as status failed with no model output in the body."""
    client = _client(_service(tmp_path, fail=True))
    gen_id = client.post("/api/jobs/7/generate", json={"kind": "resume"}).json()["id"]

    resp = client.get(f"/api/generations/{gen_id}")
    body = resp.json()
    assert body["status"] == "failed"
    assert body["outcome"] is None
    assert "SECRETMODELOUTPUT" not in resp.text


def test_download_streams_ready_docx(tmp_path):
    """A ready generation downloads as a .docx attachment."""
    client = _client(_service(tmp_path))
    gen_id = client.post("/api/jobs/7/generate", json={"kind": "resume"}).json()["id"]

    resp = client.get(f"/api/generations/{gen_id}/download")
    assert resp.status_code == 200
    assert "wordprocessingml" in resp.headers["content-type"]
    assert "resume.docx" in resp.headers.get("content-disposition", "")


def test_download_missing_file_returns_410(tmp_path):
    """A ready row whose .docx has vanished returns 410 so the chip regenerates."""
    service = _service(tmp_path)
    client = _client(service)
    gen_id = client.post("/api/jobs/7/generate", json={"kind": "resume"}).json()["id"]

    # Delete the produced file behind the row's back.
    path = service.get_generation(gen_id).file_path
    os.remove(path)

    resp = client.get(f"/api/generations/{gen_id}/download")
    assert resp.status_code == 410


def test_download_pending_returns_409(tmp_path):
    """Downloading a still-pending generation is a 409 (not ready)."""
    service = _service(tmp_path)
    # Insert a pending row directly so no background task fulfils it.
    service._generation_repo.save(
        Generation(
            id="pend1",
            job_id=7,
            kind="resume",
            status="pending",
            outcome="clean",
            file_path="",
            provider="openai",
            model="gpt-4o",
            created_at=datetime.now(),
        )
    )
    resp = _client(service).get("/api/generations/pend1/download")
    assert resp.status_code == 409


def test_poll_unknown_generation_returns_404(tmp_path):
    """Polling an unknown generation id yields a 404."""
    assert _client(_service(tmp_path)).get("/api/generations/nope").status_code == 404


def test_poll_flips_timed_out_pending_to_failed(tmp_path):
    """A pending row past its timeout self-heals to failed on the next poll."""
    service = _service(tmp_path, timeout=60)
    service._generation_repo.save(
        Generation(
            id="stale1",
            job_id=7,
            kind="resume",
            status="pending",
            outcome="clean",
            file_path="",
            provider="openai",
            model="gpt-4o",
            created_at=datetime.now() - timedelta(hours=1),
        )
    )
    body = _client(service).get("/api/generations/stale1").json()
    assert body["status"] == "failed"


def test_list_job_generations_newest_first(tmp_path):
    """The job-scoped list returns recorded generations, newest first."""
    client = _client(_service(tmp_path))
    client.post("/api/jobs/7/generate", json={"kind": "resume"})
    client.post("/api/jobs/7/generate", json={"kind": "cover_letter"})

    body = client.get("/api/jobs/7/generations").json()
    assert len(body) == 2
    assert all("filePath" not in g for g in body)
