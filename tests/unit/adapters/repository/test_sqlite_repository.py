"""Unit tests for SQLiteJobRepository.

Uses an in-memory database (or a tmp_path file where reopening matters) — no real
user files or network. The adapter under test is our own store, so it is exercised
against a real SQLite connection rather than a mock.
"""

from datetime import datetime

import pytest

from src.adapters.repository.sqlite_repository import SQLiteJobRepository
from src.core.domain.fingerprint import compute_fingerprint
from src.core.domain.job import Job
from src.core.domain.job_status import JobStatus
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory

_NOW = datetime(2026, 7, 14, 9, 0, 0)


def _repo() -> SQLiteJobRepository:
    """Return a fresh in-memory repository."""
    return SQLiteJobRepository(db_path=":memory:")


def _job(
    title: str = "Senior Software Engineer",
    company: str = "Acme Corp",
    location: str = "Remote",
    platform: str = "linkedin",
    url: str = "https://linkedin.com/jobs/1",
) -> Job:
    """Return a Job with overridable identity fields."""
    return Job(
        title=title,
        company=company,
        location=location,
        url=url,
        description="A job.",
        platform=platform,
        scraped_at=_NOW,
    )


def _match_result(job: Job, score: int = 82) -> MatchResult:
    """Return a MatchResult for the given job."""
    def _cat(mx: int) -> ScoreCategory:
        return ScoreCategory(max=mx, earned=mx, reasoning="ok")

    return MatchResult(
        job=job,
        score=score,
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


def _save(repo: SQLiteJobRepository, job: Job, score: int = 82):
    """Compute the fingerprint and persist a job with an evaluation."""
    fp = compute_fingerprint(job.company, job.title, job.location)
    return fp, repo.save_job(
        job=job,
        fingerprint=fp,
        match_result=_match_result(job, score),
        threshold=75,
        near_miss_floor=60,
        seen_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Save + find
# ---------------------------------------------------------------------------

def test_save_then_find_by_fingerprint_reuses_evaluation():
    """A saved job is found by its fingerprint with its stored MatchResult."""
    repo = _repo()
    fp, stored = _save(repo, _job(), score=82)

    found = repo.find_by_fingerprint(fp.key)
    assert found is not None
    assert found.id == stored.id
    assert found.match_result is not None
    assert found.match_result.score == 82
    assert found.threshold == 75
    assert found.near_miss_floor == 60


def test_find_by_fingerprint_miss_returns_none():
    """An unknown fingerprint returns None."""
    repo = _repo()
    assert repo.find_by_fingerprint("nobody|nothing|nowhere") is None


def test_save_records_initial_sighting():
    """save_job records the representative platform as the first sighting."""
    repo = _repo()
    _, stored = _save(repo, _job(platform="linkedin"))
    assert stored.seen_on == ["linkedin"]


# ---------------------------------------------------------------------------
# list_jobs
# ---------------------------------------------------------------------------

def test_list_jobs_empty_returns_empty_list():
    """An empty store lists no jobs."""
    assert _repo().list_jobs() == []


def test_list_jobs_orders_by_score_descending():
    """Evaluated jobs are returned strongest-first."""
    repo = _repo()
    _save(repo, _job(title="Low", url="https://x/low"), score=55)
    _save(repo, _job(title="High", url="https://x/high"), score=91)
    _save(repo, _job(title="Mid", url="https://x/mid"), score=73)

    scores = [j.match_result.score for j in repo.list_jobs()]
    assert scores == [91, 73, 55]


def test_list_jobs_places_unevaluated_last():
    """A job without an evaluation sorts after every scored job."""
    repo = _repo()
    _save(repo, _job(title="Scored", url="https://x/s"), score=40)
    unscored = _job(title="Unscored", url="https://x/u")
    fp = compute_fingerprint(unscored.company, unscored.title, unscored.location)
    repo.save_job(
        job=unscored,
        fingerprint=fp,
        match_result=None,
        threshold=None,
        near_miss_floor=None,
        seen_at=_NOW,
    )

    titles = [j.title for j in repo.list_jobs()]
    assert titles == ["Scored", "Unscored"]


def test_list_jobs_attaches_seen_on_per_job():
    """Each listed job carries its own distinct sighting platforms."""
    repo = _repo()
    _, a = _save(repo, _job(title="A", platform="linkedin", url="https://x/a"), score=90)
    _, b = _save(repo, _job(title="B", platform="indeed", url="https://x/b"), score=80)
    repo.record_sighting(a.id, "glassdoor", None, _NOW)

    by_title = {j.title: j.seen_on for j in repo.list_jobs()}
    assert by_title["A"] == ["glassdoor", "linkedin"]
    assert by_title["B"] == ["indeed"]


def test_list_jobs_uses_single_grouped_sightings_read(monkeypatch):
    """Listing N jobs must not issue a per-row get_seen_on query (no N+1)."""
    repo = _repo()
    for i in range(3):
        _save(repo, _job(title=f"J{i}", url=f"https://x/{i}"), score=80 + i)

    calls = {"n": 0}
    original = repo.get_seen_on

    def _counting(job_id):
        calls["n"] += 1
        return original(job_id)

    monkeypatch.setattr(repo, "get_seen_on", _counting)
    repo.list_jobs()
    assert calls["n"] == 0


# ---------------------------------------------------------------------------
# Sightings / seen-on
# ---------------------------------------------------------------------------

def test_seen_on_aggregates_distinct_platforms():
    """Recording sightings on multiple platforms yields a sorted distinct set."""
    repo = _repo()
    _, stored = _save(repo, _job(platform="linkedin"))
    repo.record_sighting(stored.id, "indeed", "https://indeed.com/1", _NOW)
    repo.record_sighting(stored.id, "glassdoor", None, _NOW)

    assert repo.get_seen_on(stored.id) == ["glassdoor", "indeed", "linkedin"]


def test_record_sighting_idempotent_per_platform():
    """Re-seeing a job on the same platform does not duplicate the sighting."""
    repo = _repo()
    _, stored = _save(repo, _job(platform="linkedin"))
    repo.record_sighting(stored.id, "linkedin", "https://linkedin.com/jobs/1", _NOW)
    assert repo.get_seen_on(stored.id) == ["linkedin"]


def test_record_sighting_updates_last_seen_at():
    """A later sighting advances the job's last_seen_at."""
    repo = _repo()
    _, stored = _save(repo, _job())
    later = datetime(2026, 7, 20, 12, 0, 0)
    repo.record_sighting(stored.id, "indeed", None, later)

    refreshed = repo.find_by_fingerprint(stored.fingerprint)
    assert refreshed is not None
    assert refreshed.last_seen_at == later
    assert refreshed.first_seen_at == _NOW


# ---------------------------------------------------------------------------
# Near-misses
# ---------------------------------------------------------------------------

def test_find_near_misses_same_company_title_different_location():
    """A job sharing company + title but not location is a near-miss."""
    repo = _repo()
    _save(repo, _job(location="New York, NY"))
    probe = compute_fingerprint("Acme Corp", "Senior Software Engineer", "Austin, TX")

    near = repo.find_near_misses(probe.canon_company, probe.canon_title, probe.key)
    assert len(near) == 1
    assert near[0].location == "New York, NY"


def test_find_near_misses_excludes_exact_key():
    """The job's own fingerprint is excluded from its near-misses."""
    repo = _repo()
    fp, _ = _save(repo, _job(location="Remote"))
    near = repo.find_near_misses(fp.canon_company, fp.canon_title, fp.key)
    assert near == []


def test_find_near_misses_different_title_returns_nothing():
    """A different title is distinct, not a near-miss."""
    repo = _repo()
    _save(repo, _job(title="Senior Software Engineer"))
    probe = compute_fingerprint("Acme Corp", "Data Engineer", "Austin, TX")
    assert repo.find_near_misses(probe.canon_company, probe.canon_title, probe.key) == []


# ---------------------------------------------------------------------------
# Dedup-disabled (null fingerprint)
# ---------------------------------------------------------------------------

def test_null_fingerprints_do_not_collide():
    """Two jobs whose fingerprint is empty both persist (dedup disabled)."""
    repo = _repo()
    for i in range(2):
        job = _job(company="", url=f"https://x/{i}")  # empty company -> None key
        fp = compute_fingerprint(job.company, job.title, job.location)
        assert fp.key is None
        stored = repo.save_job(
            job=job,
            fingerprint=fp,
            match_result=_match_result(job),
            threshold=75,
            near_miss_floor=60,
            seen_at=_NOW,
        )
        assert stored.fingerprint is None


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

def test_migrations_are_idempotent_across_reopen(tmp_path):
    """Reopening an existing database re-applies nothing and still works."""
    db_path = str(tmp_path / "agent.db")
    repo1 = SQLiteJobRepository(db_path=db_path)
    fp, stored = _save(repo1, _job())
    repo1.close()

    repo2 = SQLiteJobRepository(db_path=db_path)
    found = repo2.find_by_fingerprint(fp.key)
    assert found is not None
    assert found.match_result.score == 82

    versions = [
        row[0] for row in repo2._conn.execute("SELECT version FROM schema_migrations")
    ]
    assert versions == [1, 2]
    repo2.close()


# ---------------------------------------------------------------------------
# Lifecycle — status, history, saved (migration 2, ADR-025)
# ---------------------------------------------------------------------------

def _history(repo: SQLiteJobRepository, job_id: int) -> list[tuple]:
    """Return (from_status, to_status, note) history rows for a job, in order."""
    return [
        (r["from_status"], r["to_status"], r["note"])
        for r in repo._conn.execute(
            "SELECT from_status, to_status, note FROM status_history "
            "WHERE job_id = ? ORDER BY id",
            (job_id,),
        ).fetchall()
    ]


def test_saved_evaluated_job_defaults_to_evaluated_status():
    """An evaluated job persists as ``evaluated`` with a creation history row."""
    repo = _repo()
    _, stored = _save(repo, _job())
    assert stored.status is JobStatus.EVALUATED
    assert stored.saved is False
    assert _history(repo, stored.id) == [(None, "evaluated", None)]


def test_unevaluated_job_persists_as_new():
    """A job saved without an evaluation lands as ``new``."""
    repo = _repo()
    job = _job()
    fp = compute_fingerprint(job.company, job.title, job.location)
    stored = repo.save_job(
        job=job,
        fingerprint=fp,
        match_result=None,
        threshold=None,
        near_miss_floor=None,
        seen_at=_NOW,
    )
    assert stored.status is JobStatus.NEW
    assert _history(repo, stored.id) == [(None, "new", None)]


def test_set_status_records_history_and_updates_job():
    """A human transition updates the job and appends a from→to history row."""
    repo = _repo()
    _, stored = _save(repo, _job())

    changed = repo.set_status(stored.id, JobStatus.APPLIED, note="referred")
    assert changed is True

    refreshed = repo.get_job(stored.id)
    assert refreshed is not None
    assert refreshed.status is JobStatus.APPLIED
    assert _history(repo, stored.id) == [
        (None, "evaluated", None),
        ("evaluated", "applied", "referred"),
    ]


def test_set_status_idempotent_no_op_writes_no_history():
    """Setting the status to its current value changes nothing and returns False."""
    repo = _repo()
    _, stored = _save(repo, _job())
    repo.set_status(stored.id, JobStatus.APPLIED)

    before = _history(repo, stored.id)
    changed = repo.set_status(stored.id, JobStatus.APPLIED)
    assert changed is False
    assert _history(repo, stored.id) == before


def test_machine_write_never_clobbers_human_status():
    """A machine=True write over a human-set status is refused (ADR-025)."""
    repo = _repo()
    _, stored = _save(repo, _job())
    repo.set_status(stored.id, JobStatus.APPLIED)

    changed = repo.set_status(stored.id, JobStatus.EVALUATED, machine=True)
    assert changed is False

    refreshed = repo.get_job(stored.id)
    assert refreshed is not None
    assert refreshed.status is JobStatus.APPLIED
    assert ("applied", "evaluated", None) not in _history(repo, stored.id)


def test_set_status_missing_job_returns_false():
    """Transitioning an unknown job is a no-op returning False."""
    assert _repo().set_status(999, JobStatus.APPLIED) is False


def test_set_saved_toggles_without_history():
    """set_saved flips the bookmark and never writes a history row."""
    repo = _repo()
    _, stored = _save(repo, _job())
    before = _history(repo, stored.id)

    repo.set_saved(stored.id, True)
    assert repo.get_job(stored.id).saved is True
    repo.set_saved(stored.id, False)
    assert repo.get_job(stored.id).saved is False
    assert _history(repo, stored.id) == before


def test_get_job_miss_returns_none():
    """get_job returns None for an unknown id."""
    assert _repo().get_job(123) is None
