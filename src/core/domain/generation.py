"""Generation domain entity — the provenance record of one generated document (F).

Every tailored resume or cover letter is recorded here with **provenance only** —
which job it was for, which provider/model produced it, where the ``.docx`` lives,
and the formatter outcome. There is deliberately **no document-text field**:
generated content never reaches an API response, the DOM, logs, email, or stdout
(CLAUDE.md #2, ADR-029). For a ``needs_review`` outcome the record carries structural
*location hints* (e.g. "Experience → bullet 2"), never the ambiguous text itself.

F owns this entity and its ``generations`` table (§15 gap 4/7). W6 adds the async
lifecycle field (``status``) for the browser's background-generation flow — the
synchronous CLI path never leaves it at its ``ready`` default.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

GenerationKind = Literal["resume", "cover_letter"]
GenerationOutcome = Literal["clean", "repaired", "needs_review"]
GenerationStatus = Literal["pending", "ready", "failed"]


class Generation(BaseModel):
    """A persisted record of one generated document (path + provenance, no content)."""

    id: str
    """Opaque identifier, also the ``.docx`` filename stem (no name or title in it)."""

    job_id: int
    kind: GenerationKind

    status: GenerationStatus = "ready"
    """Async lifecycle state (W6). ``pending`` while the background task runs,
    ``ready`` when the ``.docx`` exists, ``failed`` on error or timeout. The
    synchronous CLI path persists an already-finished record, so it keeps this
    default. ``status`` is the source of truth for lifecycle; ``outcome`` is only
    meaningful once ``status == "ready"`` — a ``pending``/``failed`` row carries a
    placeholder ``outcome`` the API never surfaces."""

    outcome: GenerationOutcome
    file_path: str

    provider: str
    model: str

    repair_note: str = ""
    """Human-readable note of the mechanical repairs applied (repaired outcome)."""

    review_locations: list[str] = []
    """Structural locations a human should review (needs_review outcome). No content."""

    created_at: datetime
