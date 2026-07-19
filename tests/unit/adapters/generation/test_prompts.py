"""Unit tests for the generation prompts — hard rules + voice injection present."""

from src.adapters.generation.prompts import (
    COVER_LETTER_SYSTEM_PROMPT,
    COVER_LETTER_USER_PROMPT,
    FORMATTING_RULES,
    TAILOR_SYSTEM_PROMPT,
)


def test_formatting_rules_state_the_hard_rules():
    """The shared rules block names every hard formatting rule (CLAUDE.md #6)."""
    rules = FORMATTING_RULES.lower()
    assert "semicolon" in rules
    assert "em-dash" in rules
    assert "hyphen" in rules
    assert "compound word" in rules


def test_tailor_prompt_embeds_formatting_rules_and_json_shape():
    """The tailor system prompt carries the rules and asks for JSON output."""
    assert FORMATTING_RULES in TAILOR_SYSTEM_PROMPT
    assert "JSON" in TAILOR_SYSTEM_PROMPT
    assert "summary" in TAILOR_SYSTEM_PROMPT
    assert "never invent" in TAILOR_SYSTEM_PROMPT.lower()


def test_cover_letter_prompt_injects_voice_descriptor():
    """The cover-letter system prompt formats tone, person, and style notes in."""
    filled = COVER_LETTER_SYSTEM_PROMPT.format(
        tone="warm", person="implied", style_notes="Lead with outcomes."
    )
    assert "warm" in filled
    assert "implied" in filled
    assert "Lead with outcomes." in filled
    assert FORMATTING_RULES in filled
    # The JSON braces survived .format() (were correctly escaped).
    assert '"salutation"' in filled


def test_user_prompt_has_all_fields():
    """The cover-letter user template exposes every substitution field."""
    filled = COVER_LETTER_USER_PROMPT.format(
        resume_text="R", job_title="T", company="C", job_description="D", feedback=""
    )
    assert "R" in filled and "T" in filled and "C" in filled and "D" in filled
