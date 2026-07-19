"""AppSettings domain entity — the global, web-editable configuration (W7).

The operational settings that apply across all runs (as opposed to per-profile search
definitions, which are ``SearchProfile`` rows). Seeded from ``.env`` on first run and
authoritative thereafter (ADR-031). **Secret values are deliberately absent** — API
keys are handled only as masked status (never returned to a caller), so they can never
leak through this entity.
"""

from pydantic import BaseModel

from src.core.domain.voice_descriptor import VoiceDescriptor


class AppSettings(BaseModel):
    """The global operational settings, excluding secret values (ADR-031)."""

    evaluator_provider: str = "openai"
    """The LLM evaluator provider — ``openai`` or ``anthropic``."""

    evaluator_model: str | None = None
    """Optional model override; None means the provider's default model."""

    schedule_cron: str = ""
    """The APScheduler cron expression for scheduled runs (empty when unset)."""

    schedule_timezone: str = "UTC"
    """The timezone the cron expression is evaluated in."""

    enrichment_mode: str = "shadow"
    """The Gemini pre-filter mode — ``shadow`` (measure only) or ``enforce``."""

    voice: VoiceDescriptor = VoiceDescriptor()
    """The cover-letter voice descriptor (tone preset, person, style notes)."""
