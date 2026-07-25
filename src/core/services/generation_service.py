"""GenerationService — orchestrates document generation end to end (F, ADR-029).

The one place the CLI and the W6 async web task route through to turn a stored,
evaluated job into a tailored resume or cover letter ``.docx``. It loads the active
master resume (E1) and the stored job (B1), calls the generation port, runs the
deterministic formatter, performs **exactly one** corrective retry when the formatter
flags an ambiguous hyphen, writes the ``.docx`` for **every** outcome, and records a
provenance-only ``Generation`` row.

Two entry shapes share one production core (``_produce_resume`` /
``_produce_cover_letter``): the CLI calls ``generate_resume`` /
``generate_cover_letter`` synchronously and persists a finished ``ready`` record; the
web calls ``create_pending`` (a ``pending`` row returned immediately) then
``run_generation`` in a background task, which updates that same row to
``ready``/``failed`` (W6). ``get_generation`` flips a ``pending`` row that outlived
its timeout to ``failed`` so a task lost to a restart recovers on the next poll.

Privacy is structural: the LLM's document text lives only in the local ``.docx`` file
and the in-memory entity while rendering. It is never logged, never returned to a
caller, and never written to the ``Generation`` record — only paths, provenance,
outcome, repair notes, and (for ``needs_review``) structural location hints leave the
service (CLAUDE.md #2). Generation is user-triggered, so this service is **not** wired
into the scheduled ``JobSearchService``.
"""

import logging
import os
from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from src.core.domain.cover_letter import CoverLetter
from src.core.domain.generation import Generation, GenerationKind
from src.core.domain.job import Job
from src.core.domain.resume import Resume
from src.core.domain.stored_job import StoredJob
from src.core.domain.tailored_resume import ResumeSection, TailoredResume
from src.core.domain.voice_descriptor import VoiceDescriptor
from src.core.exceptions import GenerationError
from src.core.ports.cover_letter_port import CoverLetterPort
from src.core.ports.docx_writer_port import DocxWriterPort
from src.core.ports.generation_repository_port import GenerationRepositoryPort
from src.core.ports.job_repository_port import JobRepositoryPort
from src.core.ports.resume_tailor_port import ResumeTailorPort
from src.core.services.document_formatter import (
    FormatResult,
    TextSegment,
    format_segments,
)
from src.core.services.resume_service import ResumeService

logger = logging.getLogger(__name__)

_DEFAULT_GENERATIONS_DIR = "data/generations"
_DEFAULT_GENERATION_TIMEOUT_SECONDS = 120.0


class GenerationService:
    """Coordinate resume/job loading, the LLM, the formatter, the writer, and storage."""

    def __init__(
        self,
        tailor: ResumeTailorPort,
        cover_letter: CoverLetterPort,
        writer: DocxWriterPort,
        generation_repo: GenerationRepositoryPort,
        resume_service: ResumeService,
        job_repository: JobRepositoryPort,
        generations_dir: str = _DEFAULT_GENERATIONS_DIR,
        generation_timeout_seconds: float = _DEFAULT_GENERATION_TIMEOUT_SECONDS,
    ) -> None:
        """Wire the ports and services the generation pipeline coordinates.

        Args:
            tailor: The resume-tailoring adapter.
            cover_letter: The cover-letter adapter.
            writer: The ``.docx`` writer.
            generation_repo: Persistence for generation records.
            resume_service: Source of the active master resume.
            job_repository: Source of the stored job.
            generations_dir: Directory the ``.docx`` files are written to.
            generation_timeout_seconds: How long a ``pending`` async row may live
                before ``get_generation`` flips it to ``failed`` (W6).
        """
        self._tailor = tailor
        self._cover_letter = cover_letter
        self._writer = writer
        self._generation_repo = generation_repo
        self._resume_service = resume_service
        self._job_repository = job_repository
        self._generations_dir = generations_dir
        self._generation_timeout_seconds = generation_timeout_seconds

    async def generate_resume(self, job_id: int) -> Generation:
        """Generate a tailored resume ``.docx`` for the stored job ``job_id``.

        Args:
            job_id: The repository id of the job to tailor to.

        Returns:
            The persisted Generation record (provenance only, no content).

        Raises:
            GenerationError: When no resume is stored or the job id is unknown.
        """
        resume, job = self._load(job_id)
        write, result = await self._produce_resume(resume, job)
        return self._persist(
            "resume", job_id, result, write, self._tailor.provider, self._tailor.model
        )

    async def generate_cover_letter(self, job_id: int, voice: VoiceDescriptor) -> Generation:
        """Generate a cover-letter ``.docx`` for the stored job ``job_id``.

        Args:
            job_id: The repository id of the job to write a letter for.
            voice: The structured voice descriptor (ADR-030).

        Returns:
            The persisted Generation record (provenance only, no content).

        Raises:
            GenerationError: When no resume is stored or the job id is unknown.
        """
        resume, job = self._load(job_id)
        write, result = await self._produce_cover_letter(resume, job, voice)
        return self._persist(
            "cover_letter",
            job_id,
            result,
            write,
            self._cover_letter.provider,
            self._cover_letter.model,
        )

    async def create_pending(self, job_id: int, kind: GenerationKind) -> Generation:
        """Create and store a ``pending`` generation row for the async web flow (W6).

        Validates preconditions **synchronously** (via ``_load``) so the caller can
        surface a user-fixable error immediately instead of as a failed background
        job. The returned row's ``id`` is the poll handle and the ``.docx`` filename
        stem; ``run_generation`` fills it in.

        Args:
            job_id: The repository id of the job to generate for.
            kind: ``"resume"`` or ``"cover_letter"``.

        Returns:
            The persisted ``pending`` Generation record.

        Raises:
            GenerationError: When no resume is stored or the job id is unknown.
        """
        self._load(job_id)  # validate resume + job exist before returning an id
        port = self._tailor if kind == "resume" else self._cover_letter
        generation = Generation(
            id=uuid4().hex,
            job_id=job_id,
            kind=kind,
            status="pending",
            outcome="clean",  # placeholder; not surfaced until status == "ready"
            file_path="",
            provider=port.provider,
            model=port.model,
            created_at=datetime.now(),
        )
        logger.info("Started %s generation %s for job %d", kind, generation.id, job_id)
        return self._generation_repo.save(generation)

    async def run_generation(
        self, generation_id: str, voice: VoiceDescriptor | None = None
    ) -> None:
        """Run a pending generation to completion, updating its row (W6 background task).

        Loads the pending row, produces the document (LLM + formatter + one retry),
        writes ``{id}.docx``, and updates the row to ``ready`` (with the real outcome)
        or ``failed``. **Never raises** — a background task has no caller to catch it,
        and the failure is recorded on the row for the poll to report. Only the
        exception *type* is logged; the raw error can carry model output (CLAUDE.md #2).

        Args:
            generation_id: The id of the pending row to fulfil.
            voice: The voice descriptor for a cover letter (ignored for a resume).
        """
        generation = self._generation_repo.get(generation_id)
        if generation is None or generation.status != "pending":
            return  # already terminal, timed out, or gone — nothing to do

        try:
            resume, job = self._load(generation.job_id)
            if generation.kind == "resume":
                write, result = await self._produce_resume(resume, job)
            else:
                write, result = await self._produce_cover_letter(
                    resume, job, voice or VoiceDescriptor()
                )
            path = os.path.join(self._generations_dir, f"{generation.id}.docx")
            write(path)
        except Exception as exc:  # noqa: BLE001 — record failure, never crash the task
            logger.error(
                "Generation %s failed for job %d (%s)",
                generation.id,
                generation.job_id,
                type(exc).__name__,
            )
            self._generation_repo.update(generation.model_copy(update={"status": "failed"}))
            return

        self._generation_repo.update(
            generation.model_copy(
                update={
                    "status": "ready",
                    "outcome": result.outcome,
                    "file_path": path,
                    "repair_note": result.repair_note,
                    "review_locations": result.review_locations,
                }
            )
        )
        logger.info(
            "Generated %s for job %d — %s (%s)",
            generation.kind,
            generation.job_id,
            result.outcome,
            path,
        )

    def get_generation(self, generation_id: str) -> Generation | None:
        """Return a generation, flipping a timed-out ``pending`` row to ``failed`` (W6).

        The async task lives in-process, so a restart loses it and leaves the row
        ``pending`` forever. Detecting that lazily on read (``created_at`` older than
        the timeout) means the poll self-heals to ``failed`` and the chip offers Retry.

        Args:
            generation_id: The id to look up.

        Returns:
            The Generation (possibly just transitioned to ``failed``), or None.
        """
        generation = self._generation_repo.get(generation_id)
        if generation is None or generation.status != "pending":
            return generation
        age = (datetime.now() - generation.created_at).total_seconds()
        if age <= self._generation_timeout_seconds:
            return generation
        logger.warning(
            "Generation %s timed out after %.0fs — marking failed",
            generation.id,
            age,
        )
        return self._generation_repo.update(generation.model_copy(update={"status": "failed"}))

    def generations_for_job(self, job_id: int) -> list[Generation]:
        """Return every generation recorded for a job, newest first (W6 detail fan-out).

        Args:
            job_id: The repository id of the job.

        Returns:
            The job's generations ordered newest first (possibly empty).
        """
        return self._generation_repo.list_for_job(job_id)

    async def _produce_resume(
        self, resume: Resume, job: Job
    ) -> tuple[Callable[[str], None], FormatResult]:
        """Tailor + format a resume with one corrective retry; return a writer + result."""
        doc = await self._tailor.tailor(resume, job)
        formatted, result = self._format_resume(doc)
        if result.outcome == "needs_review":
            doc = await self._tailor.tailor(resume, job, feedback=_feedback(result))
            formatted, result = self._format_resume(doc)
        return lambda path: self._writer.write_resume(formatted, path), result

    async def _produce_cover_letter(
        self, resume: Resume, job: Job, voice: VoiceDescriptor
    ) -> tuple[Callable[[str], None], FormatResult]:
        """Generate + format a cover letter with one corrective retry; return writer + result."""
        doc = await self._cover_letter.generate(resume, job, voice)
        formatted, result = self._format_cover_letter(doc)
        if result.outcome == "needs_review":
            doc = await self._cover_letter.generate(resume, job, voice, feedback=_feedback(result))
            formatted, result = self._format_cover_letter(doc)
        return lambda path: self._writer.write_cover_letter(formatted, path), result

    def _load(self, job_id: int) -> tuple[Resume, Job]:
        """Load the active resume and the stored job, or raise GenerationError."""
        resume = self._resume_service.get_active()
        if resume is None:
            raise GenerationError("No master resume stored — run 'resume upload <path>' first.")
        stored = self._job_repository.get_job(job_id)
        if stored is None:
            raise GenerationError(f"No stored job {job_id}.")
        return resume, _to_job(stored)

    def _persist(
        self,
        kind: str,
        job_id: int,
        result: FormatResult,
        write: Callable[[str], None],
        provider: str,
        model: str,
    ) -> Generation:
        """Write the ``.docx`` and record the provenance-only generation row."""
        gen_id = uuid4().hex
        path = os.path.join(self._generations_dir, f"{gen_id}.docx")
        write(path)
        generation = Generation(
            id=gen_id,
            job_id=job_id,
            kind=kind,  # type: ignore[arg-type]
            outcome=result.outcome,
            file_path=path,
            provider=provider,
            model=model,
            repair_note=result.repair_note,
            review_locations=result.review_locations,
            created_at=datetime.now(),
        )
        logger.info(
            "Generated %s for job %d — %s (%s)",
            kind,
            job_id,
            result.outcome,
            path,
        )
        return self._generation_repo.save(generation)

    @staticmethod
    def _format_resume(
        doc: TailoredResume,
    ) -> tuple[TailoredResume, FormatResult]:
        """Format a tailored resume's text and rebuild it from the result."""
        segments = [TextSegment(location="Summary", text=doc.summary)]
        for section in doc.sections:
            for index, bullet in enumerate(section.bullets, start=1):
                segments.append(
                    TextSegment(location=f"{section.heading} → bullet {index}", text=bullet)
                )
        for index, skill in enumerate(doc.skills, start=1):
            segments.append(TextSegment(location=f"Skills → item {index}", text=skill))

        result = format_segments(segments)
        texts = iter(seg.text for seg in result.segments)

        summary = next(texts)
        sections = [
            ResumeSection(
                heading=section.heading,
                bullets=[next(texts) for _ in section.bullets],
            )
            for section in doc.sections
        ]
        skills = [next(texts) for _ in doc.skills]
        rebuilt = TailoredResume(summary=summary, sections=sections, skills=skills)
        return rebuilt, result

    @staticmethod
    def _format_cover_letter(
        doc: CoverLetter,
    ) -> tuple[CoverLetter, FormatResult]:
        """Format a cover letter's text and rebuild it from the result."""
        segments = [TextSegment(location="Salutation", text=doc.salutation)]
        for index, paragraph in enumerate(doc.paragraphs, start=1):
            segments.append(TextSegment(location=f"Paragraph {index}", text=paragraph))
        segments.append(TextSegment(location="Closing", text=doc.closing))

        result = format_segments(segments)
        texts = iter(seg.text for seg in result.segments)

        salutation = next(texts)
        paragraphs = [next(texts) for _ in doc.paragraphs]
        closing = next(texts)
        rebuilt = CoverLetter(salutation=salutation, paragraphs=paragraphs, closing=closing)
        return rebuilt, result


def _feedback(result: FormatResult) -> str:
    """Return the comma-joined review locations to feed back on the retry."""
    return ", ".join(result.review_locations)


def _to_job(stored: StoredJob) -> Job:
    """Map a StoredJob (persistence read model) to a Job for the generation ports."""
    return Job(
        title=stored.title,
        company=stored.company,
        location=stored.location,
        url=stored.url or "",
        description=stored.description or "",
        platform=stored.seen_on[0] if stored.seen_on else "",
        scraped_at=stored.last_seen_at,
    )
