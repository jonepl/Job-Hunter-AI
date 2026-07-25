"""Unit tests for the Anthropic generation adapters (SDK mocked, no network)."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from src.adapters.generation.anthropic_generation import (
    ClaudeCoverLetter,
    ClaudeTailor,
)
from src.core.domain.job import Job
from src.core.domain.resume import Resume
from src.core.domain.voice_descriptor import VoiceDescriptor
from src.core.exceptions import ModelNotFoundError


def _resume() -> Resume:
    """Return a minimal Resume corpus."""
    return Resume(raw_text="Ten years of backend work.", parsed_at=datetime(2026, 7, 1))


def _job() -> Job:
    """Return a minimal Job."""
    return Job(
        title="Staff Engineer",
        company="Acme",
        location="Remote",
        url="https://x/1",
        description="Build things.",
        platform="linkedin",
        scraped_at=datetime(2026, 7, 1),
    )


def _response(text: str) -> MagicMock:
    """Return a mock Anthropic message carrying ``text``."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


@pytest.mark.asyncio
async def test_tailor_parses_fenced_json():
    """The tailor strips a ```json fence and validates into a TailoredResume."""
    adapter = ClaudeTailor(api_key="sk-test")
    payload = {"summary": "Leader.", "sections": [], "skills": ["Go"]}
    adapter._client = MagicMock()
    adapter._client.messages.create = AsyncMock(
        return_value=_response("```json\n" + json.dumps(payload) + "\n```")
    )

    result = await adapter.tailor(_resume(), _job())
    assert result.summary == "Leader."
    assert result.skills == ["Go"]
    assert adapter.provider == "anthropic"
    assert adapter.model == "claude-sonnet-4-5"


@pytest.mark.asyncio
async def test_cover_letter_parses_plain_json():
    """The cover-letter adapter validates an unfenced JSON body."""
    adapter = ClaudeCoverLetter(api_key="sk-test")
    payload = {"salutation": "Hi,", "paragraphs": ["Fit."], "closing": "Thanks"}
    adapter._client = MagicMock()
    adapter._client.messages.create = AsyncMock(return_value=_response(json.dumps(payload)))

    result = await adapter.generate(_resume(), _job(), VoiceDescriptor(tone="bold"))
    assert result.closing == "Thanks"


@pytest.mark.asyncio
async def test_unknown_model_raises_model_not_found():
    """A 404 from Anthropic is re-raised as ModelNotFoundError."""
    adapter = ClaudeTailor(api_key="sk-test", model="claude-sonnet-9")
    adapter._client = MagicMock()
    adapter._client.messages.create = AsyncMock(
        side_effect=anthropic.NotFoundError(message="not found", response=MagicMock(), body=None)
    )

    with pytest.raises(ModelNotFoundError, match="claude-sonnet-9"):
        await adapter.tailor(_resume(), _job())
