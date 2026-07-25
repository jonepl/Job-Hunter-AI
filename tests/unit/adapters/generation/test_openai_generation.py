"""Unit tests for the OpenAI generation adapters (SDK mocked, no network)."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import NotFoundError

from src.adapters.generation.openai_generation import OpenAICoverLetter, OpenAITailor
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


def _response(content: str) -> MagicMock:
    """Return a mock OpenAI chat completion carrying ``content``."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
async def test_tailor_parses_structured_json():
    """The tailor validates the JSON response into a TailoredResume."""
    adapter = OpenAITailor(api_key="sk-test")
    payload = {
        "summary": "Backend leader.",
        "sections": [{"heading": "Experience", "bullets": ["Shipped a system."]}],
        "skills": ["Python"],
    }
    adapter._client = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=_response(json.dumps(payload)))

    result = await adapter.tailor(_resume(), _job())
    assert result.summary == "Backend leader."
    assert result.sections[0].bullets == ["Shipped a system."]
    assert adapter.provider == "openai"
    assert adapter.model == "gpt-4o"


@pytest.mark.asyncio
async def test_cover_letter_parses_structured_json():
    """The cover-letter adapter validates the JSON into a CoverLetter."""
    adapter = OpenAICoverLetter(api_key="sk-test")
    payload = {
        "salutation": "Dear Team,",
        "paragraphs": ["I am a fit."],
        "closing": "Sincerely",
    }
    adapter._client = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=_response(json.dumps(payload)))

    result = await adapter.generate(_resume(), _job(), VoiceDescriptor())
    assert result.salutation == "Dear Team,"
    assert result.paragraphs == ["I am a fit."]


@pytest.mark.asyncio
async def test_unknown_model_raises_model_not_found():
    """A 404 from OpenAI is re-raised as ModelNotFoundError with a clear message."""
    adapter = OpenAITailor(api_key="sk-test", model="gpt-9o")
    adapter._client = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(
        side_effect=NotFoundError("model not found", response=MagicMock(), body=None)
    )

    with pytest.raises(ModelNotFoundError, match="gpt-9o"):
        await adapter.tailor(_resume(), _job())


@pytest.mark.asyncio
async def test_retry_feedback_is_sent_in_the_prompt():
    """When feedback is passed, the correction guidance reaches the user prompt."""
    adapter = OpenAITailor(api_key="sk-test")
    create = AsyncMock(
        return_value=_response(json.dumps({"summary": "s", "sections": [], "skills": []}))
    )
    adapter._client = MagicMock()
    adapter._client.chat.completions.create = create

    await adapter.tailor(_resume(), _job(), feedback="Summary")
    user_prompt = create.call_args.kwargs["messages"][1]["content"]
    assert "REVISION NEEDED" in user_prompt
    assert "Summary" in user_prompt
