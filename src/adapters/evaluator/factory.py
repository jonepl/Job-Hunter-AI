"""Factory for selecting an EvaluatorPort implementation from env config."""

import logging
import os
import sys

from src.adapters.evaluator.anthropic_evaluator import ClaudeEvaluator
from src.adapters.evaluator.openai_evaluator import OpenAIEvaluator
from src.core.ports.evaluator_port import EvaluatorPort

logger = logging.getLogger(__name__)

_PROVIDERS: dict[str, tuple[str, type[EvaluatorPort]]] = {
    "openai": ("OPENAI_API_KEY", OpenAIEvaluator),
    "anthropic": ("ANTHROPIC_API_KEY", ClaudeEvaluator),
}


def build_evaluator() -> EvaluatorPort:
    """Instantiate and return the evaluator configured by EVALUATOR_PROVIDER.

    Reads EVALUATOR_PROVIDER from the environment to select the provider,
    then reads the corresponding API key env var. EVALUATOR_MODEL, when set,
    overrides the provider's default model (the CLI --evaluator-model flag is
    applied by writing this variable). Exits with a critical log message if the
    provider is unknown or the API key is missing.

    Returns:
        A configured EvaluatorPort implementation.

    Raises:
        SystemExit: If EVALUATOR_PROVIDER is unknown or the API key is unset.
    """
    provider = os.getenv("EVALUATOR_PROVIDER", "")

    if provider not in _PROVIDERS:
        logger.critical(
            "Unknown EVALUATOR_PROVIDER %r. Must be one of: %s",
            provider,
            ", ".join(_PROVIDERS),
        )
        sys.exit(1)

    env_key, cls = _PROVIDERS[provider]
    api_key = os.getenv(env_key, "")

    if not api_key:
        logger.critical(
            "Required environment variable %s is not set. Check your .env file.", env_key
        )
        sys.exit(1)

    model = os.getenv("EVALUATOR_MODEL") or None

    if model:
        logger.info("Evaluator registered: %s (model override: %s)", provider, model)
    else:
        logger.info("Evaluator registered: %s (provider default model)", provider)

    return cls(api_key=api_key, model=model)
