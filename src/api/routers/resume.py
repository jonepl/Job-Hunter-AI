"""Resume router — browser master-resume upload and version management (W5).

The web counterpart of the ``resume`` CLI: it exposes ``ResumeService`` (parse-once
ingest, list versions, activate) over HTTP. Routes contain no business logic
(ADR-026) — they call the service and shape its ``Resume`` entities into
provenance-only response models that never carry the resume text (ADR-028).
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.api.deps import get_resume_service
from src.api.schemas import ResumeState
from src.core.services.resume_service import ResumeService

router = APIRouter(prefix="/resume", tags=["resume"])


@router.get("", response_model=ResumeState)
def get_resume(
    service: ResumeService = Depends(get_resume_service),
) -> ResumeState:
    """Return the active master resume and its version history.

    Args:
        service: The shared ResumeService (injected).

    Returns:
        The panel state — active version plus every version, newest-first. An empty
        store yields ``{active: null, versions: []}`` (a normal empty state).
    """
    return ResumeState.from_versions(service.list_versions())


@router.post("", response_model=ResumeState)
async def upload_resume(
    file: UploadFile = File(...),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeState:
    """Parse and store an uploaded resume as the new active version.

    Identical bytes to an existing version are re-activated, not re-parsed (ADR-028).

    Args:
        file: The uploaded ``.pdf`` or ``.docx`` file.
        service: The shared ResumeService (injected).

    Returns:
        The refreshed panel state after the upload.

    Raises:
        HTTPException: 400 when the file is too large, empty, unparseable, or an
            unsupported format — with a clear message.
    """
    data = await file.read()
    try:
        service.ingest(data, file.filename or "resume")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ResumeState.from_versions(service.list_versions())


@router.post("/versions/{version}/activate", response_model=ResumeState)
def activate_version(
    version: int,
    service: ResumeService = Depends(get_resume_service),
) -> ResumeState:
    """Restore an earlier stored version as the active one.

    Args:
        version: The version number to activate.
        service: The shared ResumeService (injected).

    Returns:
        The refreshed panel state after the switch.

    Raises:
        HTTPException: 404 when no version with that number exists.
    """
    if not service.activate(version):
        raise HTTPException(status_code=404, detail=f"No stored resume version {version}")
    return ResumeState.from_versions(service.list_versions())
