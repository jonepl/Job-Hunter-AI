"""RunRecord domain entity — the lifecycle record of one web-triggered run (W8).

The web "Run search now" button kicks the same multi-profile pipeline a scheduled
fire runs, but a run takes far too long to block an HTTP request. So a ``running``
row is created and returned immediately; a background task executes the pipeline and
updates the row to ``succeeded`` or ``failed`` with a small **summary** (how many
profiles ran, how many jobs were found, how many were newly evaluated, how many
qualified). The client polls the row until a terminal status.

The record is **summary only** — counts, timing, and provenance. It carries no job
content or evaluation detail (that lives in the ``jobs`` store the pipeline writes to);
``error`` holds only an exception *type name*, never a raw message that could echo
scraped or model text (CLAUDE.md #2). ``trigger`` records what started the run so a
future CLI/scheduled row can share the table.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RunStatus = Literal["running", "succeeded", "failed"]
RunTrigger = Literal["web", "scheduled", "cli"]


class RunRecord(BaseModel):
    """A persisted record of one pipeline run (summary + lifecycle, no job content)."""

    id: str
    """Opaque identifier — the poll handle returned by ``POST /runs``."""

    status: RunStatus = "running"
    """Lifecycle state. ``running`` while the background task executes, ``succeeded``
    when every profile finished, ``failed`` on an unrecoverable error or timeout."""

    trigger: RunTrigger = "web"
    """What started the run. ``web`` today; the column is future-proofed for the
    scheduled and CLI paths to record their runs here too."""

    profiles_run: int = 0
    """How many search profiles this run executed (0 until the run finishes)."""

    jobs_found: int = 0
    """Total jobs the run evaluated across all profiles (reused + newly scored)."""

    new_jobs: int = 0
    """Jobs freshly sent to the evaluator this run (excludes dedup reuses)."""

    qualifying: int = 0
    """Jobs that scored at or above their profile threshold across all profiles."""

    error: str = ""
    """The exception *type name* when ``status == "failed"`` — never a raw message
    (CLAUDE.md #2). Empty for a running or succeeded run."""

    started_at: datetime
    """When the run was created (also the timeout clock for a lost background task)."""

    finished_at: datetime | None = None
    """When the run reached a terminal status. None while running."""
