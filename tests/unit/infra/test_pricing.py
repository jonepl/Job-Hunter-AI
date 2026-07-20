"""Unit tests for src.infra.pricing — the single source of truth for token rates.

Locks the defaults to the values previously inlined in runner.py / scheduler.py and
verifies the unknown-provider fallback preserves the old ``else`` (Anthropic) branch.
"""

from src.infra import pricing


def test_show_cost_estimate_defaults_false(monkeypatch):
    """SHOW_COST_ESTIMATE is off unless explicitly "true"."""
    monkeypatch.delenv("SHOW_COST_ESTIMATE", raising=False)
    assert pricing.show_cost_estimate() is False


def test_show_cost_estimate_true(monkeypatch):
    """SHOW_COST_ESTIMATE="true" (any case) enables tracking."""
    monkeypatch.setenv("SHOW_COST_ESTIMATE", "TRUE")
    assert pricing.show_cost_estimate() is True


def test_rates_for_openai_defaults(monkeypatch):
    """OpenAI defaults match the previous inline values (2.50 / 10.00)."""
    for var in (
        "OPENAI_INPUT_COST_PER_1M",
        "OPENAI_OUTPUT_COST_PER_1M",
    ):
        monkeypatch.delenv(var, raising=False)
    assert pricing.rates_for("openai") == (2.50, 10.00)


def test_rates_for_anthropic_defaults(monkeypatch):
    """Anthropic defaults match the previous inline values (3.00 / 15.00)."""
    for var in (
        "ANTHROPIC_INPUT_COST_PER_1M",
        "ANTHROPIC_OUTPUT_COST_PER_1M",
    ):
        monkeypatch.delenv(var, raising=False)
    assert pricing.rates_for("anthropic") == (3.00, 15.00)


def test_rates_for_unknown_provider_falls_back_to_anthropic(monkeypatch):
    """An unknown/unset provider uses the Anthropic rates (old ``else`` branch)."""
    for var in (
        "ANTHROPIC_INPUT_COST_PER_1M",
        "ANTHROPIC_OUTPUT_COST_PER_1M",
    ):
        monkeypatch.delenv(var, raising=False)
    assert pricing.rates_for("") == (3.00, 15.00)
    assert pricing.rates_for("ollama") == (3.00, 15.00)


def test_rates_for_reads_env_overrides(monkeypatch):
    """Configured rates come from .env, not hardcoded."""
    monkeypatch.setenv("OPENAI_INPUT_COST_PER_1M", "1.11")
    monkeypatch.setenv("OPENAI_OUTPUT_COST_PER_1M", "4.44")
    assert pricing.rates_for("openai") == (1.11, 4.44)
