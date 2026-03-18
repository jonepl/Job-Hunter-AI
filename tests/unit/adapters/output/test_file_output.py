"""Unit tests for the file output adapter."""

import csv
import os
from datetime import datetime

import pytest

from src.adapters.output.file_output import FileOutput
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult


@pytest.fixture
def sample_results() -> list[MatchResult]:
    """Return a list of MatchResult fixtures."""
    job = Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="Python role.",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )
    return [
        MatchResult(
            job=job,
            score=85,
            matched_skills=["Python", "REST APIs"],
            missing_skills=["Kubernetes"],
            summary="Strong match.",
        )
    ]


@pytest.mark.asyncio
async def test_deliver_writes_csv_file(tmp_path, sample_results):
    """Happy path — deliver() creates a CSV file in the output directory."""
    output = FileOutput(output_dir=str(tmp_path))
    await output.deliver(sample_results)

    files = list(tmp_path.glob("results_*.csv"))
    assert len(files) == 1


@pytest.mark.asyncio
async def test_deliver_csv_contains_correct_fields(tmp_path, sample_results):
    """Happy path — CSV file contains all required column headers and row data."""
    output = FileOutput(output_dir=str(tmp_path))
    await output.deliver(sample_results)

    csv_file = list(tmp_path.glob("results_*.csv"))[0]
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["rank"] == "1"
    assert row["title"] == "Senior Python Developer"
    assert row["company"] == "Acme Corp"
    assert row["score"] == "85"
    assert "Python" in row["matched_skills"]
    assert "Kubernetes" in row["missing_skills"]
    assert row["platform"] == "linkedin"


@pytest.mark.asyncio
async def test_deliver_does_nothing_when_results_empty(tmp_path):
    """Edge case — deliver() writes no file when results list is empty."""
    output = FileOutput(output_dir=str(tmp_path))
    await output.deliver([])

    files = list(tmp_path.glob("results_*.csv"))
    assert len(files) == 0


@pytest.mark.asyncio
async def test_deliver_creates_output_directory_if_missing(tmp_path):
    """Happy path — deliver() creates the output directory if it does not exist."""
    new_dir = str(tmp_path / "nested" / "output")
    output = FileOutput(output_dir=new_dir)
    await output.deliver(sample_results := [
        MatchResult(
            job=Job(
                title="Engineer",
                company="Corp",
                location="Remote",
                url="https://example.com",
                description="desc",
                platform="indeed",
                scraped_at=datetime(2026, 3, 17, 9, 0, 0),
            ),
            score=75,
            matched_skills=[],
            missing_skills=[],
            summary="ok",
        )
    ])

    assert os.path.isdir(new_dir)
    assert len(list(os.scandir(new_dir))) == 1
