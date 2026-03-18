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
