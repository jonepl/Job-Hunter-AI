"""Unit tests for GenerationService orchestration (fakes for every port).

Covers the three formatter outcomes, the single corrective retry, writing the .docx
for every outcome, provenance recording, the precondition errors, and — critically —
that no document content leaks onto the record or through any port argument.
"""

from datetime import datetime

import pytest

from src.core.domain.cover_letter import CoverLetter
from src.core.domain.resume import Resume
from src.core.domain.stored_job import StoredJob
from src.core.domain.tailored_resume import ResumeSection, TailoredResume
from src.core.domain.voice_descriptor import VoiceDescriptor
from src.core.exceptions import GenerationError
from src.core.ports.cover_letter_port import CoverLetterPort
from src.core.ports.docx_writer_port import DocxWriterPort
from src.core.ports.generation_repository_port import GenerationRepositoryPort
from src.core.ports.resume_tailor_port import ResumeTailorPort
from src.core.services.generation_service import GenerationService

_NOW = datetime(2026, 7, 18, 9, 0, 0)


class _FakeTailor(ResumeTailorPort):
    """A tailor returning a scripted sequence of documents, recording feedback."""

    def __init__(self, docs: list[TailoredResume]) -> None:
        self._docs = docs
        self.feedbacks: list[str | None] = []
        self.provider = "openai"
        self.model = "gpt-4o"

    async def tailor(self, resume, job, feedback=None):
        self.feedbacks.append(feedback)
        index = min(len(self.feedbacks) - 1, len(self._docs) - 1)
        return self._docs[index]


class _FakeCoverLetter(CoverLetterPort):
    """A cover-letter adapter returning a scripted sequence of letters."""

    def __init__(self, docs: list[CoverLetter]) -> None:
        self._docs = docs
        self.feedbacks: list[str | None] = []
        self.provider = "anthropic"
        self.model = "claude-sonnet-4-5"

    async def generate(self, resume, job, voice, feedback=None):
        self.feedbacks.append(feedback)
        index = min(len(self.feedbacks) - 1, len(self._docs) - 1)
        return self._docs[index]


class _FakeWriter(DocxWriterPort):
    """A writer that records calls instead of touching disk."""

    def __init__(self) -> None:
        self.resume_writes: list[tuple[TailoredResume, str]] = []
        self.letter_writes: list[tuple[CoverLetter, str]] = []

    def write_resume(self, doc, path):
        self.resume_writes.append((doc, path))

    def write_cover_letter(self, doc, path):
        self.letter_writes.append((doc, path))


class _FakeGenRepo(GenerationRepositoryPort):
    """A generation repository that records saves in memory."""

    def __init__(self) -> None:
        self.saved = []

    def save(self, generation):
        self.saved.append(generation)
        return generation

    def get(self, generation_id):
        return None

    def list_for_job(self, job_id):
        return []


class _FakeResumeService:
    """A stand-in exposing only get_active, as the service uses."""

    def __init__(self, resume: Resume | None) -> None:
        self._resume = resume

    def get_active(self) -> Resume | None:
        return self._resume


class _FakeJobRepo:
    """A stand-in exposing only get_job, as the service uses."""

    def __init__(self, job: StoredJob | None) -> None:
        self._job = job

    def get_job(self, job_id: int) -> StoredJob | None:
        return self._job


def _resume() -> Resume:
    """Return a minimal active resume."""
    return Resume(raw_text="Backend corpus.", parsed_at=_NOW, is_active=True)


def _stored_job() -> StoredJob:
    """Return a minimal stored, evaluated job."""
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


_MISSING = object()


def _service(tailor=None, cover=None, resume=_MISSING, job=_MISSING, writer=None, repo=None):
    """Assemble a GenerationService from fakes, with sensible defaults.

    ``resume``/``job`` use a sentinel default so an explicit ``None`` (meaning "no
    stored resume" / "unknown job") is honored rather than replaced with a default.
    """
    writer = writer or _FakeWriter()
    repo = repo or _FakeGenRepo()
    active_resume = _resume() if resume is _MISSING else resume
    stored_job = _stored_job() if job is _MISSING else job
    service = GenerationService(
        tailor=tailor or _FakeTailor([TailoredResume(summary="Clean summary.")]),
        cover_letter=cover or _FakeCoverLetter([CoverLetter(salutation="Hi,", closing="Bye")]),
        writer=writer,
        generation_repo=repo,
        resume_service=_FakeResumeService(active_resume),
        job_repository=_FakeJobRepo(stored_job),
        generations_dir="data/generations",
    )
    return service, writer, repo


@pytest.mark.asyncio
async def test_clean_resume_records_and_writes():
    """A clean tailor result records a clean generation and writes one .docx."""
    tailor = _FakeTailor([TailoredResume(summary="Clean summary.")])
    service, writer, repo = _service(tailor=tailor)

    gen = await service.generate_resume(7)

    assert gen.outcome == "clean"
    assert gen.provider == "openai" and gen.model == "gpt-4o"
    assert gen.file_path.startswith("data/generations/") and gen.file_path.endswith(".docx")
    assert len(writer.resume_writes) == 1
    assert repo.saved == [gen]
    assert tailor.feedbacks == [None]  # no retry


@pytest.mark.asyncio
async def test_mechanical_violation_is_repaired_without_retry():
    """A semicolon-only result is repaired in one pass (no corrective retry)."""
    tailor = _FakeTailor([TailoredResume(summary="Fast; reliable")])
    service, writer, repo = _service(tailor=tailor)

    gen = await service.generate_resume(7)

    assert gen.outcome == "repaired"
    assert "semicolon to period" in gen.repair_note
    assert tailor.feedbacks == [None]  # mechanical fixes do not trigger a retry


@pytest.mark.asyncio
async def test_needs_review_triggers_one_retry_that_can_clear_it():
    """An ambiguous hyphen triggers exactly one retry; a clean retry downgrades it."""
    ambiguous = TailoredResume(
        summary="s", sections=[ResumeSection(heading="Exp", bullets=["Acme 2020-2024"])]
    )
    clean = TailoredResume(
        summary="s", sections=[ResumeSection(heading="Exp", bullets=["Acme 2020 to 2024"])]
    )
    tailor = _FakeTailor([ambiguous, clean])
    service, _, _ = _service(tailor=tailor)

    gen = await service.generate_resume(7)

    assert len(tailor.feedbacks) == 2  # one retry
    assert tailor.feedbacks[1] is not None  # feedback fed back
    assert gen.outcome == "clean"


@pytest.mark.asyncio
async def test_persistent_ambiguity_stays_needs_review_and_still_writes():
    """If the retry is still ambiguous, the .docx is written and locations recorded."""
    ambiguous = TailoredResume(
        summary="s", sections=[ResumeSection(heading="Exp", bullets=["Acme 2020-2024"])]
    )
    tailor = _FakeTailor([ambiguous])  # every call returns the ambiguous doc
    service, writer, repo = _service(tailor=tailor)

    gen = await service.generate_resume(7)

    assert len(tailor.feedbacks) == 2  # capped at one retry
    assert gen.outcome == "needs_review"
    assert gen.review_locations == ["Exp → bullet 1"]
    assert len(writer.resume_writes) == 1  # written despite needs_review


@pytest.mark.asyncio
async def test_cover_letter_uses_voice_and_records_provider():
    """A cover letter records the cover-letter adapter's provenance."""
    cover = _FakeCoverLetter([CoverLetter(salutation="Hi,", paragraphs=["Fit."], closing="Bye")])
    service, writer, repo = _service(cover=cover)

    gen = await service.generate_cover_letter(7, VoiceDescriptor(tone="warm"))

    assert gen.kind == "cover_letter"
    assert gen.provider == "anthropic"
    assert len(writer.letter_writes) == 1


@pytest.mark.asyncio
async def test_no_active_resume_raises_generation_error():
    """Generating with no stored resume is a clean GenerationError."""
    service, _, _ = _service(resume=None)
    with pytest.raises(GenerationError, match="No master resume"):
        await service.generate_resume(7)


@pytest.mark.asyncio
async def test_unknown_job_raises_generation_error():
    """Generating for an unknown job id is a clean GenerationError."""
    service, _, _ = _service(job=None)
    with pytest.raises(GenerationError, match="No stored job"):
        await service.generate_resume(7)


@pytest.mark.asyncio
async def test_generation_record_never_contains_document_content():
    """No document text reaches the persisted record (CLAUDE.md #2)."""
    secret = "UNIQUEDOCUMENTBODY42"
    tailor = _FakeTailor([TailoredResume(summary=secret)])
    service, _, repo = _service(tailor=tailor)

    gen = await service.generate_resume(7)

    assert secret not in gen.model_dump_json()
    assert secret not in repo.saved[0].model_dump_json()
