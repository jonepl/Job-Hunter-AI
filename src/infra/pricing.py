"""Token-pricing configuration — the single source of truth for cost rates.

``SHOW_COST_ESTIMATE`` and the four per-1M rate variables live in ``.env`` and were
previously read inline in both ``runner.py`` and ``scheduler.py``. Centralizing them
here keeps those two entrypoints and the settings API from drifting into three copies
of the same defaults. Rates are ``.env``-owned and read-only in the browser; ``docs/env.md``
remains the variable source of truth.
"""

import os

# Per-1M-token defaults, matching the previous inline values exactly. OpenAI has its own
# rates; any other provider (Anthropic, or an unset provider) falls back to Anthropic's —
# preserving the old ``if provider == "openai" ... else ...`` branch.
_OPENAI_INPUT_DEFAULT = "2.50"
_OPENAI_OUTPUT_DEFAULT = "10.00"
_ANTHROPIC_INPUT_DEFAULT = "3.00"
_ANTHROPIC_OUTPUT_DEFAULT = "15.00"


def show_cost_estimate() -> bool:
    """Whether cost tracking is enabled (SHOW_COST_ESTIMATE, default false)."""
    return os.getenv("SHOW_COST_ESTIMATE", "false").lower() == "true"


def rates_for(provider: str) -> tuple[float, float]:
    """(input, output) cost per 1M tokens for the provider, from .env.

    Args:
        provider: The evaluator provider name (e.g. ``"openai"`` or ``"anthropic"``).
            Any value other than ``"openai"`` uses the Anthropic rates, preserving the
            previous ``else`` branch for both Anthropic and an unset provider.

    Returns:
        A ``(input_cost_per_1m, output_cost_per_1m)`` tuple of dollar rates.
    """
    if provider.lower() == "openai":
        input_rate = float(os.getenv("OPENAI_INPUT_COST_PER_1M", _OPENAI_INPUT_DEFAULT))
        output_rate = float(os.getenv("OPENAI_OUTPUT_COST_PER_1M", _OPENAI_OUTPUT_DEFAULT))
    else:
        input_rate = float(os.getenv("ANTHROPIC_INPUT_COST_PER_1M", _ANTHROPIC_INPUT_DEFAULT))
        output_rate = float(os.getenv("ANTHROPIC_OUTPUT_COST_PER_1M", _ANTHROPIC_OUTPUT_DEFAULT))
    return input_rate, output_rate
