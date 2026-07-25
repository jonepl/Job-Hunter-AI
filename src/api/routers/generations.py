"""Generations router — async document generation over the browser (W6, ADR-029).

Exposes Story F's ``GenerationService`` to the SPA. An LLM call is too slow to block
an HTTP request, so ``POST /jobs/{id}/generate`` creates a ``pending`` row, schedules
the work as a FastAPI background task, and returns the id immediately (202); the
client polls ``GET /generations/{id}`` via React Query until a terminal status, then
downloads the ``.docx`` from ``GET /generations/{id}/download`` (ADR-034 §3).

Routes contain no business logic (ADR-026): they call the service and shape its
entities. **No route returns document content** — only provenance, status, outcome,
and structural location hints; the file itself is streamed, never rendered.
"""

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from src.api.deps import get_generation_service
from src.api.schemas import GenerateRequest, GenerationOut
from src.core.domain.voice_descriptor import VoiceDescriptor
from src.core.exceptions import GenerationError
from src.core.services.generation_service import GenerationService

router = APIRouter(tags=["generations"])

_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_DOWNLOAD_FILENAMES = {"resume": "resume.docx", "cover_letter": "cover-letter.docx"}


@router.post("/jobs/{job_id}/generate", response_model=GenerationOut, status_code=202)
async def start_generation(
    job_id: int,
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationOut:
    """Start an async resume/cover-letter generation and return its pending record.

    Preconditions (a stored master resume, a known job) are checked synchronously so
    a user-fixable problem is a clear 400 rather than a silently failed background job.

    Args:
        job_id: The repository id of the job to generate for.
        body: The generation kind and, for a cover letter, the optional voice.
        background_tasks: FastAPI's post-response task runner.
        service: The shared GenerationService (injected).

    Returns:
        The pending GenerationOut (poll it via ``GET /generations/{id}``).

    Raises:
        HTTPException: 400 when no resume is stored or the job id is unknown.
    """
    try:
        generation = await service.create_pending(job_id, body.kind)
    except GenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    voice = _resolve_voice(body)
    background_tasks.add_task(service.run_generation, generation.id, voice)
    return GenerationOut.from_generation(generation)


@router.get("/jobs/{job_id}/generations", response_model=list[GenerationOut])
def list_job_generations(
    job_id: int,
    service: GenerationService = Depends(get_generation_service),
) -> list[GenerationOut]:
    """List every generation recorded for a job, newest first (the chip's initial state).

    Args:
        job_id: The repository id of the job.
        service: The shared GenerationService (injected).

    Returns:
        The job's generations as provenance-only response models.
    """
    return [GenerationOut.from_generation(g) for g in service.generations_for_job(job_id)]


@router.get("/generations/{generation_id}", response_model=GenerationOut)
def poll_generation(
    generation_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationOut:
    """Return one generation's current state, flipping a timed-out pending row to failed.

    Args:
        generation_id: The id returned by the generate call.
        service: The shared GenerationService (injected).

    Returns:
        The generation's current GenerationOut.

    Raises:
        HTTPException: 404 when no generation has that id.
    """
    generation = service.get_generation(generation_id)
    if generation is None:
        raise HTTPException(status_code=404, detail=f"No generation {generation_id}")
    return GenerationOut.from_generation(generation)


@router.get("/generations/{generation_id}/download")
def download_generation(
    generation_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> FileResponse:
    """Stream a ready generation's ``.docx`` (never its content in JSON).

    Args:
        generation_id: The id of the generation to download.
        service: The shared GenerationService (injected).

    Returns:
        A FileResponse streaming the ``.docx`` with a friendly filename.

    Raises:
        HTTPException: 404 unknown id; 409 not yet ready; 410 when the ``ready``
            row's file is missing on disk (the chip falls back to regenerate,
            ADR-034 §3).
    """
    generation = service.get_generation(generation_id)
    if generation is None:
        raise HTTPException(status_code=404, detail=f"No generation {generation_id}")
    if generation.status != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Generation {generation_id} is {generation.status}, not ready.",
        )
    if not generation.file_path or not os.path.isfile(generation.file_path):
        raise HTTPException(
            status_code=410,
            detail="The generated file is no longer available — regenerate it.",
        )
    return FileResponse(
        generation.file_path,
        media_type=_DOCX_MEDIA_TYPE,
        filename=_DOWNLOAD_FILENAMES.get(generation.kind, "document.docx"),
    )


def _resolve_voice(body: GenerateRequest) -> VoiceDescriptor:
    """Resolve the voice: the request's, else the env-seeded default (W7 adds the UI)."""
    if body.voice is not None:
        return body.voice.to_descriptor()
    return VoiceDescriptor(
        tone=os.getenv("VOICE_TONE", "direct"),
        person=os.getenv("VOICE_PERSON", "first_person"),
        style_notes=os.getenv("VOICE_STYLE_NOTES", ""),
    )
