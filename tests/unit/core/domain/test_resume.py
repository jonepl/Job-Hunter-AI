"""Unit tests for the Resume domain entity."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.core.domain.resume import Resume


def test_resume_valid_instantiation():
    """Happy path — Resume model accepts all valid required fields."""
    resume = Resume(
        raw_text="Experienced Python developer with 5 years...",
        parsed_at=datetime(2026, 3, 17, 9, 0, 0),
    )
    assert resume.raw_text == "Experienced Python developer with 5 years..."
    assert resume.parsed_at == datetime(2026, 3, 17, 9, 0, 0)


def test_resume_provenance_defaults():
    """The E1 provenance fields default to a v1, inactive, empty-provenance state."""
    resume = Resume(
        raw_text="corpus",
        parsed_at=datetime(2026, 3, 17, 9, 0, 0),
    )
    assert resume.version == 1
    assert resume.filename == ""
    assert resume.size_bytes == 0
    assert resume.content_hash == ""
    assert resume.skill_count == 0
    assert resume.role_count == 0
    assert resume.is_active is False
    assert resume.uploaded_at is None


def test_resume_accepts_full_provenance():
    """A stored resume carries version, filename, size, hash, counts, and active flag."""
    uploaded = datetime(2026, 3, 17, 9, 0, 0)
    resume = Resume(
        raw_text="corpus",
        parsed_at=uploaded,
        version=3,
        filename="resume.pdf",
        size_bytes=42_000,
        content_hash="abc123",
        skill_count=12,
        role_count=4,
        is_active=True,
        uploaded_at=uploaded,
    )
    assert resume.version == 3
    assert resume.filename == "resume.pdf"
    assert resume.size_bytes == 42_000
    assert resume.content_hash == "abc123"
    assert resume.skill_count == 12
    assert resume.role_count == 4
    assert resume.is_active is True
    assert resume.uploaded_at == uploaded


def test_resume_missing_required_field_raises_validation_error():
    """Validation failure — omitting raw_text raises ValidationError."""
    with pytest.raises(ValidationError):
        Resume(
            parsed_at=datetime(2026, 3, 17, 9, 0, 0),
            # raw_text is missing
        )


def test_resume_wrong_field_type_raises_validation_error():
    """Validation failure — passing wrong type for parsed_at raises ValidationError."""
    with pytest.raises(ValidationError):
        Resume(
            raw_text="Experienced Python developer with 5 years...",
            parsed_at="not-a-datetime",
        )
