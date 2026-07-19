"""Resume management for the Job Hunter AI Agent — the ``resume`` CLI backend.

Manages the cached master resume (ADR-028): upload (parse once + store a new
active version), list versions, and activate (restore) an earlier version.
Contains no CLI/argparse dependency and accepts plain Python objects, so the
future ``POST /resume`` API path (W5) can reuse the same ``ResumeService``.
"""

import logging

from src.core.services.resume_service import ResumeService

logger = logging.getLogger(__name__)


def run_resume_upload(service: ResumeService, path: str) -> tuple[str, int]:
    """Parse and cache the resume at ``path`` as the active version.

    Identical bytes to an existing version are not re-parsed or duplicated — that
    version is reactivated instead.

    Args:
        service: The ResumeService to ingest through.
        path: Filesystem path to the resume PDF.

    Returns:
        A (message, exit code) tuple. Exit code 0 on success, 1 on a bad file
        (missing, too large, or unparseable).
    """
    try:
        resume = service.ingest_path(path)
    except FileNotFoundError:
        return f"No resume file at {path}.", 1
    except ValueError as exc:
        return f"Could not store resume: {exc}", 1

    message = (
        f"Stored master resume v{resume.version} from {resume.filename} "
        f"({resume.size_bytes} bytes, ~{resume.skill_count} skills, "
        f"~{resume.role_count} roles) — now active."
    )
    logger.info(message)
    return message, 0


def run_resume_list(service: ResumeService) -> tuple[str, int]:
    """List every stored resume version, marking the active one.

    Args:
        service: The ResumeService to read from.

    Returns:
        A (message, exit code) tuple. Exit code 0 always (an empty store is a
        valid, non-error state).
    """
    versions = service.list_versions()
    if not versions:
        return "No master resume stored yet. Run: resume upload <path>", 0

    lines = ["Stored master resume versions (newest first):"]
    for r in versions:
        marker = "* " if r.is_active else "  "
        uploaded = r.uploaded_at.isoformat() if r.uploaded_at else "unknown"
        lines.append(
            f"{marker}v{r.version} — {r.filename} "
            f"(~{r.skill_count} skills, ~{r.role_count} roles, uploaded {uploaded})"
        )
    return "\n".join(lines), 0


def run_resume_activate(service: ResumeService, version: int) -> tuple[str, int]:
    """Restore an earlier stored version as the active one.

    Args:
        service: The ResumeService to mutate through.
        version: The version number to activate.

    Returns:
        A (message, exit code) tuple. Exit code 0 on success, 1 when no version
        with that number exists.
    """
    if service.activate(version):
        message = f"Master resume v{version} is now active."
        logger.info(message)
        return message, 0
    return f"No stored resume version {version}.", 1
