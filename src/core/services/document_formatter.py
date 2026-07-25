"""Deterministic three-outcome formatter for generated documents (F, ADR-029).

The one place the hard formatting rules live (CLAUDE.md #6): no semicolons, ``•``
bullets only, em-dashes banned everywhere, hyphens only inside compound words. An
LLM will not perfectly honor them, so this post-processor enforces them **after**
generation — pure, no I/O, no LLM — and it is trusted over the model, never the
reverse.

It classifies each violation into one of two classes and yields one of three
outcomes:

- **Mechanical** (unambiguous character fix) → repaired deterministically:
  ``;`` → ``.``, em-dash (``—``) → ``,``, a leading ``-``/``*`` bullet marker → ``•``.
- **Semantic-adjacent** (the hyphen trap) → never guessed. A hyphen between two
  letters (``full-stack``) is a compound word and kept. Any *other* hyphen —
  ``2020-2024``, ``Python - 5 years`` — could be a date or number a blind repair
  would corrupt, so it is flagged, a ``[PLACEHOLDER: review]`` marker is added to the
  line, and its structural location is recorded for a human.

Outcomes: ``clean`` (no violations), ``repaired`` (only mechanical, all fixed),
``needs_review`` (any surviving semantic-adjacent flag). The en-dash (``–``) is left
untouched — it is not banned and is a legitimate date separator, so rewriting it
would risk exactly the corruption the hyphen rule guards against.
"""

import re
from typing import Literal

from pydantic import BaseModel

Outcome = Literal["clean", "repaired", "needs_review"]

_SEMICOLON = re.compile(r"\s*;\s*")
_EM_DASH = re.compile(r"\s*—\s*")  # U+2014 — banned everywhere (CLAUDE.md #6)
_BULLET_MARKER = re.compile(r"^(\s*)[-*]\s+")
_HYPHEN = re.compile(r"-")

_REVIEW_MARKER = " [PLACEHOLDER: review]"


class TextSegment(BaseModel):
    """One labelled unit of document text (a summary line, a bullet, a paragraph).

    ``location`` is a **structural** hint only (e.g. ``"Experience → bullet 2"``),
    never content — it is what a ``needs_review`` outcome exposes to a human.
    """

    location: str
    text: str


class FormatResult(BaseModel):
    """The formatted segments plus the outcome and its provenance (no content leak)."""

    segments: list[TextSegment]
    outcome: Outcome
    repair_note: str = ""
    review_locations: list[str] = []


def format_segments(segments: list[TextSegment]) -> FormatResult:
    """Apply the hard formatting rules to ``segments`` and classify the outcome.

    Mechanical violations are repaired in place; semantic-adjacent hyphens are
    flagged (marker added, location recorded) but never rewritten. Numbers and dates
    are therefore never silently altered.

    Args:
        segments: The labelled text units of one generated document.

    Returns:
        A FormatResult with the (possibly repaired/marked) segments, the outcome, a
        human-readable repair note, and the structural locations needing review.
    """
    out: list[TextSegment] = []
    repairs: list[str] = []
    review_locations: list[str] = []

    for seg in segments:
        new_text, seg_repairs, flagged = _process(seg.text)
        out.append(TextSegment(location=seg.location, text=new_text))
        for repair in seg_repairs:
            if repair not in repairs:
                repairs.append(repair)
        if flagged:
            review_locations.append(seg.location)

    if review_locations:
        outcome: Outcome = "needs_review"
    elif repairs:
        outcome = "repaired"
    else:
        outcome = "clean"

    return FormatResult(
        segments=out,
        outcome=outcome,
        repair_note=", ".join(repairs),
        review_locations=review_locations,
    )


def _process(text: str) -> tuple[str, list[str], bool]:
    """Format one segment's text; return (new_text, mechanical_repairs, flagged).

    Args:
        text: The raw segment text.

    Returns:
        A tuple of the processed text, the distinct mechanical repairs applied, and
        whether a semantic-adjacent hyphen was flagged for review.
    """
    repairs: list[str] = []

    replaced = _BULLET_MARKER.sub(r"\1• ", text)
    if replaced != text:
        repairs.append("bullet marker to •")
    text = replaced

    if ";" in text:
        repairs.append("semicolon to period")
        text = _SEMICOLON.sub(". ", text).rstrip()

    if "—" in text:
        repairs.append("em-dash to comma")
        text = _EM_DASH.sub(", ", text)

    flagged = _has_ambiguous_hyphen(text)
    if flagged:
        text = text + _REVIEW_MARKER

    return text, repairs, flagged


def _has_ambiguous_hyphen(text: str) -> bool:
    """Return True when ``text`` has a hyphen that is not a compound-word hyphen.

    A compound-word hyphen (letter-hyphen-letter, e.g. ``full-stack``) is allowed.
    Any other hyphen is semantic-adjacent — adjacent to a digit or used as a
    separator (``2020-2024``, ``Python - 5 years``) — and must never be blindly
    rewritten, so it is flagged for human review.

    Args:
        text: The segment text to inspect.

    Returns:
        True when at least one ambiguous hyphen is present.
    """
    return any(not _is_compound_hyphen(text, m.start()) for m in _HYPHEN.finditer(text))


def _is_compound_hyphen(text: str, index: int) -> bool:
    """Return True when the hyphen at ``index`` sits between two ASCII letters.

    Args:
        text: The text containing the hyphen.
        index: The index of the hyphen character.

    Returns:
        True for a ``letter-hyphen-letter`` compound word, else False.
    """
    if index == 0 or index + 1 >= len(text):
        return False
    before, after = text[index - 1], text[index + 1]
    return before.isascii() and before.isalpha() and after.isascii() and after.isalpha()
