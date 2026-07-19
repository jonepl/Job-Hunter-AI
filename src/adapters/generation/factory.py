"""Factory for the document-generation adapters (F, ADR-029).

Selects the tailor + cover-letter provider from ``TAILOR_PROVIDER`` and enforces the
**hard privacy allowlist** (CLAUDE.md #1): generation ports may only ever run against
``openai`` or ``anthropic`` — never Gemini or any other provider — and an invalid
provider (or a missing API key) **fails at startup**, not mid-run. This mirrors
``evaluator/factory.py``. The ``.docx`` writer is provider-independent.
"""

import logging
import os
import sys

from src.adapters.generation.anthropic_generation import (
    ClaudeCoverLetter,
    ClaudeTailor,
)
from src.adapters.generation.docx_writer import DocxWriter
from src.adapters.generation.openai_generation import (
    OpenAICoverLetter,
    OpenAITailor,
)
from src.core.ports.cover_letter_port import CoverLetterPort
from src.core.ports.docx_writer_port import DocxWriterPort
from src.core.ports.resume_tailor_port import ResumeTailorPort

logger = logging.getLogger(__name__)

# The privacy allowlist (ADR-022/029): generation may only run against these two.
_PROVIDERS: dict[str, tuple[str, type, type]] = {
    "openai": ("OPENAI_API_KEY", OpenAITailor, OpenAICoverLetter),
    "anthropic": ("ANTHROPIC_API_KEY", ClaudeTailor, ClaudeCoverLetter),
}


def _resolve() -> tuple[str, type, type, str | None]:
    """Resolve the generation provider from env, failing fast on any bad config.

    Returns:
        A tuple of (api_key, tailor_cls, cover_letter_cls, model_override).

    Raises:
        SystemExit: When ``TAILOR_PROVIDER`` is outside the allowlist or its API
            key is unset.
    """
    provider = os.getenv("TAILOR_PROVIDER", "openai").strip().lower()

    if provider not in _PROVIDERS:
        logger.critical(
            "Invalid TAILOR_PROVIDER %r. Document generation only permits: %s "
            "(hard allowlist — ADR-022/029).",
            provider,
            ", ".join(_PROVIDERS),
        )
        sys.exit(1)

    env_key, tailor_cls, cover_cls = _PROVIDERS[provider]
    api_key = os.getenv(env_key, "")
    if not api_key:
        logger.critical(
            "Required environment variable %s is not set. Check your .env file.",
            env_key,
        )
        sys.exit(1)

    model = os.getenv("TAILOR_MODEL") or None
    logger.info(
        "Generation provider registered: %s (%s)",
        provider,
        f"model override: {model}" if model else "provider default model",
    )
    return api_key, tailor_cls, cover_cls, model


def build_resume_tailor() -> ResumeTailorPort:
    """Build the resume-tailoring adapter for the configured provider.

    Returns:
        A configured ResumeTailorPort implementation.

    Raises:
        SystemExit: On an invalid provider or missing API key.
    """
    api_key, tailor_cls, _, model = _resolve()
    return tailor_cls(api_key=api_key, model=model)


def build_cover_letter() -> CoverLetterPort:
    """Build the cover-letter adapter for the configured provider.

    Returns:
        A configured CoverLetterPort implementation.

    Raises:
        SystemExit: On an invalid provider or missing API key.
    """
    api_key, _, cover_cls, model = _resolve()
    return cover_cls(api_key=api_key, model=model)


def build_docx_writer() -> DocxWriterPort:
    """Build the ``.docx`` writer (provider-independent).

    Returns:
        A ready DocxWriter.
    """
    return DocxWriter()
