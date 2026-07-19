"""Resume domain entity.

The candidate's master resume — a single comprehensive corpus applied to all
search profiles (ADR-028). Enriched **in place** (same type, richer fields)
rather than split into a new entity, so ``ResumeTailorPort.tailor(resume, …)``
(F) consumes it with no interface change. E1 adds provenance fields (version,
filename, size, hash, parsed counts) around the ``raw_text`` corpus; full
structured-section extraction is deferred to F, where it is consumed.
"""

from datetime import datetime

from pydantic import BaseModel


class Resume(BaseModel):
    """The parsed candidate resume corpus plus its storage provenance.

    ``raw_text`` is the corpus every run evaluates against. The remaining fields
    are provenance the API/UI may surface (never the content itself, ADR-028):
    which file it came from, how large it was, which stored version it is, and
    approximate parsed counts. ``skill_count``/``role_count`` are best-effort
    heuristics over ``raw_text`` — indicative, not authoritative.
    """

    raw_text: str
    parsed_at: datetime
    version: int = 1
    filename: str = ""
    size_bytes: int = 0
    content_hash: str = ""
    skill_count: int = 0
    role_count: int = 0
    is_active: bool = False
    uploaded_at: datetime | None = None
