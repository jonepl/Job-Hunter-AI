"""Document generation for the Job Hunter AI Agent — the ``generate`` CLI backend.

Turns a stored, evaluated job into a tailored resume or cover-letter ``.docx`` (F).
Contains no CLI/argparse dependency and accepts plain Python objects, so the future
async web path (W6) can reuse the same ``GenerationService``.

Privacy is enforced here too (CLAUDE.md #2): the messages report only the outcome,
the file path, the repair note, and structural review locations — never document
content. A failed LLM call is reported by its exception **type only**; the raw error
can carry model output (e.g. a malformed-JSON snippet), so it is never echoed to
stdout or logged.
"""

import logging

from src.core.domain.generation import Generation
from src.core.domain.voice_descriptor import VoiceDescriptor
from src.core.exceptions import GenerationError, ModelNotFoundError
from src.core.services.generation_service import GenerationService

logger = logging.getLogger(__name__)

_LABELS = {"resume": "Tailored resume", "cover_letter": "Cover letter"}


async def run_generate_resume(service: GenerationService, job_id: int) -> tuple[str, int]:
    """Generate a tailored resume for ``job_id``.

    Args:
        service: The GenerationService to generate through.
        job_id: The repository id of the job to tailor to.

    Returns:
        A (message, exit code) tuple. Exit 0 for any produced document (clean,
        repaired, or needs_review); 1 on a precondition or provider failure.
    """
    try:
        generation = await service.generate_resume(job_id)
    except (GenerationError, ModelNotFoundError) as exc:
        return str(exc), 1
    except Exception as exc:  # noqa: BLE001 — never echo content-bearing detail
        logger.error("Resume generation failed for job %d (%s)", job_id, type(exc).__name__)
        return _provider_failure("resume", exc), 1
    return _describe(generation), 0


async def run_generate_cover_letter(
    service: GenerationService, job_id: int, voice: VoiceDescriptor
) -> tuple[str, int]:
    """Generate a cover letter for ``job_id`` in the given voice.

    Args:
        service: The GenerationService to generate through.
        job_id: The repository id of the job to write a letter for.
        voice: The structured voice descriptor.

    Returns:
        A (message, exit code) tuple. Exit 0 for any produced document; 1 on a
        precondition or provider failure.
    """
    try:
        generation = await service.generate_cover_letter(job_id, voice)
    except (GenerationError, ModelNotFoundError) as exc:
        return str(exc), 1
    except Exception as exc:  # noqa: BLE001 — never echo content-bearing detail
        logger.error("Cover-letter generation failed for job %d (%s)", job_id, type(exc).__name__)
        return _provider_failure("cover letter", exc), 1
    return _describe(generation), 0


def _describe(generation: Generation) -> str:
    """Render a provenance-only success message (never document content)."""
    label = _LABELS[generation.kind]
    lines = [
        f"{label} generated [{generation.outcome}] for job {generation.job_id} "
        f"→ {generation.file_path}"
    ]
    if generation.outcome == "repaired" and generation.repair_note:
        lines.append(f"  Auto-repaired formatting: {generation.repair_note}.")
    if generation.outcome == "needs_review":
        lines.append("  Needs review at: " + ", ".join(generation.review_locations) + ".")
        lines.append("  The .docx was written with [PLACEHOLDER: review] markers.")
    return "\n".join(lines)


def _provider_failure(kind: str, exc: Exception) -> str:
    """Return a safe failure message naming only the exception type, no content."""
    return (
        f"Could not generate {kind} — the generation provider call failed "
        f"({type(exc).__name__}). Check the API key, TAILOR_MODEL, and provider status."
    )
