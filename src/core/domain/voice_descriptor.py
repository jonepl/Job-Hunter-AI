"""VoiceDescriptor domain entity — how a generated cover letter should sound (F).

Voice is a **structured descriptor**, not pasted writing samples (ADR-030): a tone
preset, a first-person toggle, and free-text style notes the model follows as
instructions. Style notes are *configuration*, not personal writing, so this
introduces **no raw-text privacy exception** — the provenance-only storage rule
(ADR-028) stays unbroken. The voice is persisted in the ``settings`` table later
(W7); F accepts it as input with defaults seeded from the environment.
"""

from typing import Literal

from pydantic import BaseModel

Tone = Literal["direct", "warm", "formal", "bold"]
Person = Literal["first_person", "implied"]


class VoiceDescriptor(BaseModel):
    """A structured description of the desired cover-letter voice (ADR-030)."""

    tone: Tone = "direct"
    person: Person = "first_person"
    style_notes: str = ""
