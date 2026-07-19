"""Unit tests for the evaluator prompt templates."""

from src.adapters.evaluator.prompts import SYSTEM_PROMPT, USER_PROMPT


def test_system_prompt_has_corpus_aware_instruction():
    """The system prompt tells the evaluator to score relevant experience (gap 8b).

    The master resume is a comprehensive corpus (ADR-028), so the evaluator must
    not read breadth as a scattered trajectory or weak signal.
    """
    lowered = SYSTEM_PROMPT.lower()
    assert "corpus" in lowered
    assert "relevant experience" in lowered
    # It must explicitly protect the two categories breadth would otherwise dent.
    assert "career trajectory" in lowered
    assert "resume signal quality" in lowered


def test_user_prompt_keeps_resume_and_job_placeholders():
    """The user prompt still interpolates the resume and job description."""
    assert "{resume_text}" in USER_PROMPT
    assert "{job_description}" in USER_PROMPT
