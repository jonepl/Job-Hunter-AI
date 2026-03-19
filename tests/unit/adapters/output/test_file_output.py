"""Unit tests for the file output adapter."""

import csv
import os
from datetime import datetime

import pytest

from src.adapters.output.file_output import FileOutput, _CSV_FIELDS
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory


def _make_score_breakdown() -> ScoreBreakdown:
    """Return a valid ScoreBreakdown for use in file output tests."""
    return ScoreBreakdown(
        role_alignment=ScoreCategory(max=20, earned=18, reasoning="Strong alignment."),
        technical_stack_match=ScoreCategory(max=15, earned=13, reasoning="Good stack."),
        system_design_architecture=ScoreCategory(max=15, earned=11, reasoning="Solid design."),
        impact_and_metrics=ScoreCategory(max=15, earned=12, reasoning="Clear impact."),
        domain_industry_experience=ScoreCategory(max=10, earned=8, reasoning="Relevant domain."),
        problem_space_relevance=ScoreCategory(max=10, earned=7, reasoning="On point."),
        ownership_and_leadership=ScoreCategory(max=10, earned=9, reasoning="Strong ownership."),
        resume_signal_quality=ScoreCategory(max=3, earned=3, reasoning="Clean resume."),
        career_trajectory=ScoreCategory(max=2, earned=2, reasoning="Upward trajectory."),
    )


def _make_job(**kwargs) -> Job:
    """Return a Job instance with sensible defaults, overridable via kwargs."""
    defaults = dict(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="Python role.",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )
    return Job(**{**defaults, **kwargs})


def _make_match_result(**kwargs) -> MatchResult:
    """Return a MatchResult with sensible defaults, overridable via kwargs."""
    defaults = dict(
        job=_make_job(),
        score=85,
        seniority_level="Senior/Staff",
        years_experience_detected=7,
        hire_recommendation="Strong Yes",
        score_breakdown=_make_score_breakdown(),
        matched_skills=["Python", "REST APIs"],
        missing_skills=["Kubernetes"],
        summary="Strong match.",
    )
    return MatchResult(**{**defaults, **kwargs})


@pytest.fixture
def sample_results() -> list[MatchResult]:
    """Return a list of MatchResult fixtures."""
    return [_make_match_result()]


@pytest.mark.asyncio
async def test_deliver_writes_csv_file(tmp_path, sample_results):
    """Happy path — deliver() creates a CSV file in the output directory."""
    output = FileOutput(output_dir=str(tmp_path))
    await output.deliver(sample_results)

    files = list(tmp_path.glob("results_*.csv"))
    assert len(files) == 1


@pytest.mark.asyncio
async def test_deliver_csv_has_32_columns(tmp_path, sample_results):
    """Happy path — CSV file has exactly 32 columns."""
    assert len(_CSV_FIELDS) == 32

    output = FileOutput(output_dir=str(tmp_path))
    await output.deliver(sample_results)

    csv_file = list(tmp_path.glob("results_*.csv"))[0]
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

    assert len(headers) == 32


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
    assert row["job_title"] == "Senior Python Developer"
    assert row["company"] == "Acme Corp"
    assert row["score"] == "85"
    assert row["hire_recommendation"] == "Strong Yes"
    assert row["seniority_level"] == "Senior/Staff"
    assert row["years_experience_detected"] == "7"
    assert row["platform"] == "linkedin"
    assert row["role_alignment_earned"] == "18"
    assert row["role_alignment_max"] == "20"
    assert row["career_trajectory_earned"] == "2"
    assert row["career_trajectory_max"] == "2"


@pytest.mark.asyncio
async def test_deliver_csv_matched_skills_are_pipe_separated(tmp_path, sample_results):
    """Happy path — matched_skills in CSV are pipe-separated."""
    output = FileOutput(output_dir=str(tmp_path))
    await output.deliver(sample_results)

    csv_file = list(tmp_path.glob("results_*.csv"))[0]
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = list(reader)[0]

    assert "Python|REST APIs" == row["matched_skills"]
    assert "Kubernetes" == row["missing_skills"]


@pytest.mark.asyncio
async def test_deliver_csv_years_experience_none_written_as_empty(tmp_path):
    """Edge case — years_experience_detected=None writes as empty string in CSV."""
    result = _make_match_result(years_experience_detected=None)
    output = FileOutput(output_dir=str(tmp_path))
    await output.deliver([result])

    csv_file = list(tmp_path.glob("results_*.csv"))[0]
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = list(reader)[0]

    assert row["years_experience_detected"] == ""


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
    await output.deliver([
        _make_match_result(
            job=_make_job(
                title="Engineer",
                company="Corp",
                location="Remote",
                url="https://example.com",
                description="desc",
                platform="indeed",
            ),
            score=75,
            matched_skills=[],
            missing_skills=[],
            summary="ok",
        )
    ])

    assert os.path.isdir(new_dir)
    assert len(list(os.scandir(new_dir))) == 1
