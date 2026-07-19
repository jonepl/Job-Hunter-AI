"""Unit tests for the VoiceDescriptor domain entity (ADR-030)."""

import pytest
from pydantic import ValidationError

from src.core.domain.voice_descriptor import VoiceDescriptor


def test_voice_descriptor_defaults():
    """The default voice is direct, first-person, with no style notes."""
    voice = VoiceDescriptor()
    assert voice.tone == "direct"
    assert voice.person == "first_person"
    assert voice.style_notes == ""


def test_voice_descriptor_accepts_valid_presets():
    """Every documented tone and person value is accepted."""
    voice = VoiceDescriptor(tone="bold", person="implied", style_notes="Be brief.")
    assert voice.tone == "bold"
    assert voice.person == "implied"
    assert voice.style_notes == "Be brief."


def test_voice_descriptor_rejects_unknown_tone():
    """A tone outside the four presets is rejected by validation."""
    with pytest.raises(ValidationError):
        VoiceDescriptor(tone="whimsical")


def test_voice_descriptor_rejects_unknown_person():
    """A point of view outside the two options is rejected by validation."""
    with pytest.raises(ValidationError):
        VoiceDescriptor(person="third_person")
