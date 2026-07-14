"""Factory for the optional Gemini pre-filter (JobEnrichmentPort)."""

import logging
import os

from src.adapters.enrichment.gemini_enrichment import GeminiEnrichment
from src.core.ports.job_enrichment_port import JobEnrichmentPort

logger = logging.getLogger(__name__)


def build_enrichment() -> JobEnrichmentPort | None:
    """Build the pre-filter adapter, or None when it is disabled.

    The pre-filter is an opt-in optimisation. It is disabled (returns None) when
    ENRICHMENT_ENABLED is not truthy, or when it is enabled but GEMINI_API_KEY is
    missing — a missing key degrades to "no pre-filter" rather than failing the
    run, since evaluation still works without it.

    Returns:
        A configured JobEnrichmentPort, or None when the pre-filter is disabled.
    """
    enabled = os.getenv("ENRICHMENT_ENABLED", "false").strip().lower() == "true"
    if not enabled:
        logger.info("Pre-filter disabled (ENRICHMENT_ENABLED is not 'true').")
        return None

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning(
            "ENRICHMENT_ENABLED=true but GEMINI_API_KEY is not set — "
            "pre-filter disabled for this run."
        )
        return None

    model = os.getenv("GEMINI_MODEL") or None
    if model:
        logger.info("Pre-filter registered: gemini (model override: %s)", model)
    else:
        logger.info("Pre-filter registered: gemini (default model)")

    return GeminiEnrichment(api_key=api_key, model=model)
