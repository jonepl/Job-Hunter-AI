"""GenerationService — orchestrates document generation end to end (F, ADR-029).

The one place the CLI (and later the W6 async task) route through to turn a stored,
evaluated job into a tailored resume or cover letter ``.docx``. It loads the active
master resume (E1) and the stored job (B1), calls the generation port, runs the
deterministic formatter, performs **exactly one** corrective retry when the formatter
flags an ambiguous hyphen, writes the ``.docx`` for **every** outcome, and records a
provenance-only ``Generation`` row.

Privacy is structural: the LLM's document text lives only in the local ``.docx`` file
and the in-memory entity while rendering. It is never logged, never returned to a
caller, and never written to the ``Generation`` record — only paths, provenance,
outcome, repair notes, and (for ``needs_review``) structural location hints leave the
service (CLAUDE.md #2). Generation is user-triggered, so this service is **not** wired
into the scheduled ``JobSearchService``.
"""

import logging
import os
from datetime import datetime
from typing import Callable
from uuid import uuid4

from src.core.domain.cover_letter import CoverLetter
from src.core.domain.generation import Generation
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
        """
        self._tailor = tailor
        self._cover_letter = cover_letter
        self._writer = writer
        self._generation_repo = generation_repo
        self._resume_service = resume_service
        self._job_repository = job_repository
        self._generations_dir = generations_dir

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

        doc = await self._tailor.tailor(resume, job)
        formatted, result = self._format_resume(doc)
        if result.outcome == "needs_review":
            doc = await self._tailor.tailor(resume, job, feedback=_feedback(result))
            formatted, result = self._format_resume(doc)

        return self._persist(
            "resume",
            job_id,
            result,
            lambda path: self._writer.write_resume(formatted, path),
            self._tailor.provider,
            self._tailor.model,
        )

    async def generate_cover_letter(
        self, job_id: int, voice: VoiceDescriptor
    ) -> Generation:
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

        doc = await self._cover_letter.generate(resume, job, voice)
        formatted, result = self._format_cover_letter(doc)
        if result.outcome == "needs_review":
            doc = await self._cover_letter.generate(
                resume, job, voice, feedback=_feedback(result)
            )
            formatted, result = self._format_cover_letter(doc)

        return self._persist(
            "cover_letter",
            job_id,
            result,
            lambda path: self._writer.write_cover_letter(formatted, path),
            self._cover_letter.provider,
            self._cover_letter.model,
        )

    def _load(self, job_id: int) -> tuple[Resume, Job]:
        """Load the active resume and the stored job, or raise GenerationError."""
        resume = self._resume_service.get_active()
        if resume is None:
            raise GenerationError(
                "No master resume stored — run 'resume upload <path>' first."
            )
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
                    TextSegment(
                        location=f"{section.heading} → bullet {index}", text=bullet
                    )
                )
        for index, skill in enumerate(doc.skills, start=1):
            segments.append(
                TextSegment(location=f"Skills → item {index}", text=skill)
            )

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
            segments.append(
                TextSegment(location=f"Paragraph {index}", text=paragraph)
            )
        segments.append(TextSegment(location="Closing", text=doc.closing))

        result = format_segments(segments)
        texts = iter(seg.text for seg in result.segments)

        salutation = next(texts)
        paragraphs = [next(texts) for _ in doc.paragraphs]
        closing = next(texts)
        rebuilt = CoverLetter(
            salutation=salutation, paragraphs=paragraphs, closing=closing
        )
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
