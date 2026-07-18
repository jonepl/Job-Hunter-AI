"""Unit tests for the StatusHistoryEntry domain model."""

from datetime import datetime

from src.core.domain.job_status import JobStatus
from src.core.domain.status_history_entry import StatusHistoryEntry


def test_creation_entry_has_null_from_status():
    """The creation row transitions from None (no prior state)."""
    entry = StatusHistoryEntry(
        to_status=JobStatus.EVALUATED,
        changed_at=datetime(2026, 7, 14, 9, 0, 0),
    )
    assert entry.from_status is None
    assert entry.to_status is JobStatus.EVALUATED
    assert entry.note is None


def test_transition_entry_records_from_to_and_note():
    """A later row records the state it moved from and to, plus a note."""
    entry = StatusHistoryEntry(
        from_status=JobStatus.EVALUATED,
        to_status=JobStatus.APPLIED,
        changed_at=datetime(2026, 7, 15, 10, 0, 0),
        note="referred",
    )
    assert entry.from_status is JobStatus.EVALUATED
    assert entry.to_status is JobStatus.APPLIED
    assert entry.note == "referred"
