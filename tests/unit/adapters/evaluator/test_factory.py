"""Unit tests for the evaluator factory."""

from unittest.mock import patch

import pytest

from src.adapters.evaluator.anthropic_evaluator import ClaudeEvaluator
from src.adapters.evaluator.factory import build_evaluator
from src.adapters.evaluator.openai_evaluator import OpenAIEvaluator


def test_build_evaluator_returns_openai_evaluator():
    """Returns an OpenAIEvaluator when EVALUATOR_PROVIDER=openai."""
    env = {"EVALUATOR_PROVIDER": "openai", "OPENAI_API_KEY": "test-openai-key"}
    with patch.dict("os.environ", env, clear=False):
        evaluator = build_evaluator()
    assert isinstance(evaluator, OpenAIEvaluator)


def test_build_evaluator_returns_claude_evaluator():
    """Returns a ClaudeEvaluator when EVALUATOR_PROVIDER=anthropic."""
    env = {"EVALUATOR_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-anthropic-key"}
    with patch.dict("os.environ", env, clear=False):
        evaluator = build_evaluator()
    assert isinstance(evaluator, ClaudeEvaluator)


def test_build_evaluator_exits_on_unknown_provider():
    """Calls sys.exit when EVALUATOR_PROVIDER is not a known provider."""
    env = {"EVALUATOR_PROVIDER": "gemini"}
    with patch.dict("os.environ", env, clear=False):
        with pytest.raises(SystemExit):
            build_evaluator()


def test_build_evaluator_exits_when_provider_unset():
    """Calls sys.exit when EVALUATOR_PROVIDER is not set."""
    with patch.dict("os.environ", {}, clear=False):
        # Remove the key if present so the env var is truly absent
        with patch("os.getenv", return_value=""):
            with pytest.raises(SystemExit):
                build_evaluator()


def test_build_evaluator_exits_when_openai_api_key_missing():
    """Calls sys.exit when EVALUATOR_PROVIDER=openai but OPENAI_API_KEY is absent."""
    env = {"EVALUATOR_PROVIDER": "openai", "OPENAI_API_KEY": ""}
    with patch.dict("os.environ", env, clear=False):
        with pytest.raises(SystemExit):
            build_evaluator()


def test_build_evaluator_exits_when_anthropic_api_key_missing():
    """Calls sys.exit when EVALUATOR_PROVIDER=anthropic but ANTHROPIC_API_KEY is absent."""
    env = {"EVALUATOR_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": ""}
    with patch.dict("os.environ", env, clear=False):
        with pytest.raises(SystemExit):
            build_evaluator()


def test_build_evaluator_only_requires_relevant_api_key():
    """Only the API key for the selected provider is required; the other may be absent."""
    env = {"EVALUATOR_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}
    # Ensure ANTHROPIC_API_KEY is not set
    with patch.dict("os.environ", env, clear=False):
        with patch("os.getenv", side_effect=lambda k, default="": env.get(k, default)):
            evaluator = build_evaluator()
    assert isinstance(evaluator, OpenAIEvaluator)
