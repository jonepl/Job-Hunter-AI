"""Unit tests for the Job domain entity."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.core.domain.job import Job


def test_job_valid_instantiation():
    """Happy path — Job model accepts all valid required fields."""
    job = Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="We need a Python expert...",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )
    assert job.title == "Senior Python Developer"
    assert job.company == "Acme Corp"
    assert job.location == "Remote"
    assert job.url == "https://linkedin.com/jobs/123"
    assert job.description == "We need a Python expert..."
    assert job.platform == "linkedin"
    assert job.scraped_at == datetime(2026, 3, 17, 9, 0, 0)


def test_job_missing_required_field_raises_validation_error():
    """Validation failure — omitting a required field raises ValidationError."""
    with pytest.raises(ValidationError):
        Job(
            company="Acme Corp",
            location="Remote",
            url="https://linkedin.com/jobs/123",
            description="We need a Python expert...",
            platform="linkedin",
            scraped_at=datetime(2026, 3, 17, 9, 0, 0),
            # title is missing
        )


def test_job_wrong_field_type_raises_validation_error():
    """Validation failure — passing wrong type for scraped_at raises ValidationError."""
    with pytest.raises(ValidationError):
        Job(
            title="Senior Python Developer",
            company="Acme Corp",
            location="Remote",
            url="https://linkedin.com/jobs/123",
            description="We need a Python expert...",
            platform="linkedin",
            scraped_at="not-a-datetime",
        )
