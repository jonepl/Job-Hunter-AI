"""Anthropic generation adapters — tailored resume + cover letter (F).

The Anthropic siblings of the OpenAI generation adapters, mirroring
``anthropic_evaluator.py``: prompt-based JSON enforcement with fenced-block
stripping. As with the OpenAI adapters, a generation failure is **propagated** (F's
CLI reports it and exits non-zero); a wrong model raises ``ModelNotFoundError``.
"""

import json
import logging

import anthropic
from anthropic import AsyncAnthropic

from src.adapters.generation.prompts import (
    COVER_LETTER_SYSTEM_PROMPT,
    COVER_LETTER_USER_PROMPT,
    FEEDBACK_TEMPLATE,
    TAILOR_SYSTEM_PROMPT,
    TAILOR_USER_PROMPT,
)
from src.core.domain.cover_letter import CoverLetter
from src.core.domain.job import Job
from src.core.domain.resume import Resume
from src.core.domain.tailored_resume import TailoredResume
from src.core.domain.voice_descriptor import VoiceDescriptor
from src.core.exceptions import ModelNotFoundError
from src.core.ports.cover_letter_port import CoverLetterPort
from src.core.ports.resume_tailor_port import ResumeTailorPort

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-5"


def _feedback_block(feedback: str | None) -> str:
    """Return the retry-feedback block for a user prompt, or empty string."""
    return FEEDBACK_TEMPLATE.format(locations=feedback) if feedback else ""


async def _call_json(
    client: AsyncAnthropic, model: str, system: str, user: str
) -> dict:
    """Call Claude, strip any code fence, and return the parsed JSON object.

    Args:
        client: The AsyncAnthropic client.
        model: The model name.
        system: The system prompt.
        user: The user prompt.

    Returns:
        The parsed JSON object.

    Raises:
        ModelNotFoundError: When the model does not exist for Anthropic.
    """
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.4,
        )
    except anthropic.NotFoundError as exc:
        raise ModelNotFoundError(
            f"Anthropic model {model!r} not found. Check TAILOR_MODEL, or unset it "
            f"to use the default."
        ) from exc

    raw = (response.content[0].text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


class ClaudeTailor(ResumeTailorPort):
    """Tailor a resume to one job using Anthropic Claude."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Initialise with an Anthropic API key and optional model override.

        Args:
            api_key: Anthropic API key.
            model: Optional model override; falls back to ``claude-sonnet-4-5``.
        """
        self._client = AsyncAnthropic(api_key=api_key)
        self.provider = "anthropic"
        self.model = model or _MODEL

    async def tailor(
        self,
        resume: Resume,
        job: Job,
        feedback: str | None = None,
    ) -> TailoredResume:
        """Tailor ``resume`` to ``job`` and return structured content."""
        logger.info("Claude — tailoring resume for %r @ %s", job.title, job.company)
        user = TAILOR_USER_PROMPT.format(
            resume_text=resume.raw_text,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
            feedback=_feedback_block(feedback),
        )
        data = await _call_json(self._client, self.model, TAILOR_SYSTEM_PROMPT, user)
        return TailoredResume(**data)


class ClaudeCoverLetter(CoverLetterPort):
    """Generate a cover letter for one job using Anthropic Claude."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Initialise with an Anthropic API key and optional model override.

        Args:
            api_key: Anthropic API key.
            model: Optional model override; falls back to ``claude-sonnet-4-5``.
        """
        self._client = AsyncAnthropic(api_key=api_key)
        self.provider = "anthropic"
        self.model = model or _MODEL

    async def generate(
        self,
        resume: Resume,
        job: Job,
        voice: VoiceDescriptor,
        feedback: str | None = None,
    ) -> CoverLetter:
        """Generate a cover letter for ``job`` in the candidate's voice."""
        logger.info("Claude — cover letter for %r @ %s", job.title, job.company)
        system = COVER_LETTER_SYSTEM_PROMPT.format(
            tone=voice.tone,
            person=voice.person,
            style_notes=voice.style_notes or "(none)",
        )
        user = COVER_LETTER_USER_PROMPT.format(
            resume_text=resume.raw_text,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
            feedback=_feedback_block(feedback),
        )
        data = await _call_json(self._client, self.model, system, user)
        return CoverLetter(**data)
