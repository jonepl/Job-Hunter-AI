"""Unit tests for src/mark_runner.py — the ``mark`` CLI backend.

Exercised against a real in-memory SQLiteJobRepository (our own store), not a
mock, so the guard behavior is verified end-to-end.
"""

from datetime import datetime

from src.adapters.repository.sqlite_repository import SQLiteJobRepository
from src.core.domain.fingerprint import compute_fingerprint
from src.core.domain.job import Job
from src.core.domain.job_status import JobStatus
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.orchestration.mark_runner import run_mark

_NOW = datetime(2026, 7, 14, 9, 0, 0)


def _match_result(job: Job) -> MatchResult:
    """Return a minimal MatchResult for the given job."""
    def _cat(mx: int) -> ScoreCategory:
        return ScoreCategory(max=mx, earned=mx, reasoning="ok")

    return MatchResult(
        job=job,
        score=82,
        seniority_level="Senior",
        years_experience_detected=8,
        hire_recommendation="Yes",
        score_breakdown=ScoreBreakdown(
            role_alignment=_cat(20),
            technical_stack_match=_cat(15),
            system_design_architecture=_cat(15),
            impact_and_metrics=_cat(15),
            domain_industry_experience=_cat(10),
            problem_space_relevance=_cat(10),
            ownership_and_leadership=_cat(10),
            resume_signal_quality=_cat(3),
            career_trajectory=_cat(2),
        ),
        matched_skills=["python"],
        missing_skills=[],
        summary="Strong fit.",
    )


def _repo_with_job() -> tuple[SQLiteJobRepository, int]:
    """Return a repo holding one evaluated job and that job's id."""
    repo = SQLiteJobRepository(db_path=":memory:")
    job = Job(
        title="Senior Software Engineer",
        company="Acme",
        location="Remote",
        url="https://x/1",
        description="A job.",
        platform="linkedin",
        scraped_at=_NOW,
    )
    fp = compute_fingerprint(job.company, job.title, job.location)
    stored = repo.save_job(
        job=job,
        fingerprint=fp,
        match_result=_match_result(job),
        threshold=75,
        near_miss_floor=60,
        seen_at=_NOW,
    )
    return repo, stored.id


def test_run_mark_sets_status():
    """Marking a status updates the job and reports success (exit 0)."""
    repo, job_id = _repo_with_job()
    message, code = run_mark(repo, job_id, status=JobStatus.APPLIED, note="referred")
    assert code == 0
    assert "status → applied" in message
    assert repo.get_job(job_id).status is JobStatus.APPLIED


def test_run_mark_idempotent_status_reports_no_change():
    """Re-marking the same status is a no-op (still exit 0, 'no change')."""
    repo, job_id = _repo_with_job()
    run_mark(repo, job_id, status=JobStatus.APPLIED)
    message, code = run_mark(repo, job_id, status=JobStatus.APPLIED)
    assert code == 0
    assert "no change" in message


def test_run_mark_save_and_unsave():
    """--save then --unsave toggles the bookmark."""
    repo, job_id = _repo_with_job()
    _, code = run_mark(repo, job_id, saved=True)
    assert code == 0
    assert repo.get_job(job_id).saved is True

    run_mark(repo, job_id, saved=False)
    assert repo.get_job(job_id).saved is False


def test_run_mark_status_and_save_together():
    """A single call can change both status and save state."""
    repo, job_id = _repo_with_job()
    message, code = run_mark(repo, job_id, status=JobStatus.OFFER, saved=True)
    assert code == 0
    assert "status → offer" in message
    assert "saved" in message
    stored = repo.get_job(job_id)
    assert stored.status is JobStatus.OFFER
    assert stored.saved is True


def test_run_mark_missing_job_exits_nonzero():
    """Marking an unknown job returns exit code 1."""
    repo = SQLiteJobRepository(db_path=":memory:")
    message, code = run_mark(repo, 999, status=JobStatus.APPLIED)
    assert code == 1
    assert "No job with id 999" in message


def test_run_mark_nothing_requested_exits_two():
    """Calling with neither status nor save returns exit code 2."""
    repo, job_id = _repo_with_job()
    message, code = run_mark(repo, job_id)
    assert code == 2
    assert "Nothing to do" in message
