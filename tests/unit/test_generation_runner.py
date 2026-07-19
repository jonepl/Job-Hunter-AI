"""Unit tests for src/generation_runner.py — the ``generate`` CLI backend.

Verifies the outcome messaging, exit codes, and — critically — that neither a
success message nor a failure message ever carries document content (CLAUDE.md #2).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.domain.generation import Generation
from src.core.domain.voice_descriptor import VoiceDescriptor
from src.core.exceptions import GenerationError, ModelNotFoundError
from src.generation_runner import run_generate_cover_letter, run_generate_resume


def _generation(**overrides) -> Generation:
    """Return a Generation with defaults and optional overrides."""
    fields = {
        "id": "gen1",
        "job_id": 7,
        "kind": "resume",
        "outcome": "clean",
        "file_path": "data/generations/gen1.docx",
        "provider": "openai",
        "model": "gpt-4o",
        "created_at": datetime(2026, 7, 18, 9, 0, 0),
    }
    fields.update(overrides)
    return Generation(**fields)


def _service(**methods) -> MagicMock:
    """Return a fake GenerationService with async methods set from ``methods``."""
    service = MagicMock()
    for name, value in methods.items():
        setattr(service, name, value)
    return service


@pytest.mark.asyncio
async def test_clean_resume_reports_path_and_exit_zero():
    """A clean resume reports the outcome and path with exit 0."""
    service = _service(generate_resume=AsyncMock(return_value=_generation()))
    message, code = await run_generate_resume(service, 7)

    assert code == 0
    assert "data/generations/gen1.docx" in message
    assert "clean" in message


@pytest.mark.asyncio
async def test_repaired_reports_repair_note():
    """A repaired outcome surfaces the repair note."""
    service = _service(
        generate_resume=AsyncMock(
            return_value=_generation(outcome="repaired", repair_note="semicolon to period")
        )
    )
    message, code = await run_generate_resume(service, 7)

    assert code == 0
    assert "semicolon to period" in message


@pytest.mark.asyncio
async def test_needs_review_lists_locations_only():
    """A needs_review outcome lists structural locations, never content."""
    service = _service(
        generate_resume=AsyncMock(
            return_value=_generation(
                outcome="needs_review",
                review_locations=["Summary", "Experience → bullet 2"],
            )
        )
    )
    message, code = await run_generate_resume(service, 7)

    assert code == 0
    assert "Experience → bullet 2" in message
    assert "[PLACEHOLDER: review]" in message


@pytest.mark.asyncio
async def test_generation_error_reports_message_and_exit_one():
    """A precondition error is reported verbatim with exit 1."""
    service = _service(
        generate_resume=AsyncMock(side_effect=GenerationError("No master resume stored."))
    )
    message, code = await run_generate_resume(service, 7)

    assert code == 1
    assert "No master resume stored." in message


@pytest.mark.asyncio
async def test_model_not_found_is_surfaced():
    """A ModelNotFoundError message (safe, no content) is surfaced with exit 1."""
    service = _service(
        generate_resume=AsyncMock(side_effect=ModelNotFoundError("model 'x' not found"))
    )
    message, code = await run_generate_resume(service, 7)

    assert code == 1
    assert "not found" in message


@pytest.mark.asyncio
async def test_provider_failure_never_echoes_content():
    """A content-bearing LLM error is reported by type only — never its detail."""
    secret = "LEAKEDDOCUMENTTEXT99"
    service = _service(
        generate_resume=AsyncMock(side_effect=ValueError(f"bad json: {secret}"))
    )
    message, code = await run_generate_resume(service, 7)

    assert code == 1
    assert secret not in message
    assert "ValueError" in message


@pytest.mark.asyncio
async def test_cover_letter_success():
    """A cover letter reports its path and label with exit 0."""
    service = _service(
        generate_cover_letter=AsyncMock(
            return_value=_generation(kind="cover_letter", file_path="data/generations/c.docx")
        )
    )
    message, code = await run_generate_cover_letter(service, 7, VoiceDescriptor())

    assert code == 0
    assert "Cover letter" in message
    assert "data/generations/c.docx" in message
