"""OpenAI generation adapters — tailored resume + cover letter (F).

Two sibling adapters (ADR-029 keeps the ports separate) sharing one JSON-call
helper, mirroring ``openai_evaluator.py``. They return the structured entity; the
deterministic formatter and the ``.docx`` writer run afterward in the service.

Unlike the evaluator — which degrades a flaky call to a low-score result — a
generation failure is **propagated**: F's synchronous CLI path reports it and exits
non-zero rather than writing a bogus document (the async ``failed`` status is W6). A
wrong model still raises ``ModelNotFoundError`` for a clear, actionable message.
"""

import json
import logging

from openai import AsyncOpenAI, NotFoundError

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

_MODEL = "gpt-4o"


def _feedback_block(feedback: str | None) -> str:
    """Return the retry-feedback block for a user prompt, or empty string."""
    return FEEDBACK_TEMPLATE.format(locations=feedback) if feedback else ""


async def _call_json(client: AsyncOpenAI, model: str, system: str, user: str) -> dict:
    """Call OpenAI in JSON mode and return the parsed object.

    Args:
        client: The AsyncOpenAI client.
        model: The model name.
        system: The system prompt.
        user: The user prompt.

    Returns:
        The parsed JSON object.

    Raises:
        ModelNotFoundError: When the model does not exist for OpenAI.
    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
    except NotFoundError as exc:
        raise ModelNotFoundError(
            f"OpenAI model {model!r} not found. Check TAILOR_MODEL, or unset it to "
            f"use the default."
        ) from exc
    raw = response.choices[0].message.content or ""
    return json.loads(raw)


class OpenAITailor(ResumeTailorPort):
    """Tailor a resume to one job using OpenAI."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Initialise with an OpenAI API key and optional model override.

        Args:
            api_key: OpenAI API key.
            model: Optional model override; falls back to ``gpt-4o``.
        """
        self._client = AsyncOpenAI(api_key=api_key)
        self.provider = "openai"
        self.model = model or _MODEL

    async def tailor(
        self,
        resume: Resume,
        job: Job,
        feedback: str | None = None,
    ) -> TailoredResume:
        """Tailor ``resume`` to ``job`` and return structured content."""
        logger.info("OpenAI — tailoring resume for %r @ %s", job.title, job.company)
        user = TAILOR_USER_PROMPT.format(
            resume_text=resume.raw_text,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
            feedback=_feedback_block(feedback),
        )
        data = await _call_json(self._client, self.model, TAILOR_SYSTEM_PROMPT, user)
        return TailoredResume(**data)


class OpenAICoverLetter(CoverLetterPort):
    """Generate a cover letter for one job using OpenAI."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Initialise with an OpenAI API key and optional model override.

        Args:
            api_key: OpenAI API key.
            model: Optional model override; falls back to ``gpt-4o``.
        """
        self._client = AsyncOpenAI(api_key=api_key)
        self.provider = "openai"
        self.model = model or _MODEL

    async def generate(
        self,
        resume: Resume,
        job: Job,
        voice: VoiceDescriptor,
        feedback: str | None = None,
    ) -> CoverLetter:
        """Generate a cover letter for ``job`` in the candidate's voice."""
        logger.info("OpenAI — cover letter for %r @ %s", job.title, job.company)
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
