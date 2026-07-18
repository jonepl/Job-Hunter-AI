"""Unit tests for the StoredJob domain model."""

from datetime import datetime

from src.core.domain.job_status import JobStatus
from src.core.domain.stored_job import StoredJob


def _stored(**overrides) -> StoredJob:
    """Return a StoredJob with sensible defaults, overridable via kwargs."""
    defaults = dict(
        id=1,
        company="Acme",
        title="Engineer",
        location="Remote",
        url="https://x/1",
        fingerprint="acme|engineer|remote us",
        fingerprint_version=1,
        canon_company="acme",
        canon_title="engineer",
        canon_location="remote us",
        first_seen_at=datetime(2026, 7, 14, 9, 0, 0),
        last_seen_at=datetime(2026, 7, 14, 9, 0, 0),
    )
    return StoredJob(**{**defaults, **overrides})


def test_stored_job_defaults():
    """Optional evaluation and sighting fields default to None/empty."""
    job = _stored()
    assert job.match_result is None
    assert job.threshold is None
    assert job.near_miss_floor is None
    assert job.seen_on == []
    assert job.status is JobStatus.NEW
    assert job.saved is False


def test_stored_job_carries_status_and_saved():
    """status and saved round-trip the lifecycle fields (ADR-025)."""
    job = _stored(status=JobStatus.APPLIED, saved=True)
    assert job.status is JobStatus.APPLIED
    assert job.saved is True


def test_stored_job_allows_null_fingerprint():
    """A dedup-disabled job stores a None fingerprint."""
    job = _stored(fingerprint=None)
    assert job.fingerprint is None


def test_stored_job_carries_seen_on():
    """seen_on holds the platforms the job was sighted on."""
    job = _stored(seen_on=["indeed", "linkedin"])
    assert job.seen_on == ["indeed", "linkedin"]
