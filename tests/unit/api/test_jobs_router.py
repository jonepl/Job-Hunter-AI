"""Unit tests for GET /api/jobs.

Exercises the router in-process via FastAPI's TestClient against a real in-memory
SQLite repository injected through a dependency override — no network, no real
files, consistent with the mock-all-externals rule (the store is our own).
"""

from datetime import datetime

from fastapi.testclient import TestClient

from src.adapters.repository.sqlite_repository import SQLiteJobRepository
from src.api.deps import get_repository
from src.api.main import create_app
from src.core.domain.fingerprint import compute_fingerprint
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory

_NOW = datetime(2026, 7, 14, 9, 0, 0)


def _job(title: str, company: str = "Acme Corp", url: str = "https://x/1") -> Job:
    """Return a Job with an overridable title/company/url."""
    return Job(
        title=title,
        company=company,
        location="Remote",
        url=url,
        description="A job.",
        platform="linkedin",
        scraped_at=_NOW,
    )


def _match_result(job: Job, score: int) -> MatchResult:
    """Return a MatchResult for the given job and score."""

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


def _seed(repo: SQLiteJobRepository, title: str, score: int, url: str) -> int:
    """Persist an evaluated job into the repository and return its id."""
    job = _job(title, url=url)
    fp = compute_fingerprint(job.company, job.title, job.location)
    stored = repo.save_job(
        job=job,
        fingerprint=fp,
        match_result=_match_result(job, score),
        threshold=75,
        near_miss_floor=60,
        seen_at=_NOW,
    )
    return stored.id


def _client(repo: SQLiteJobRepository) -> TestClient:
    """Return a TestClient whose repository dependency is the given repo."""
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def test_list_jobs_empty_returns_empty_array():
    """An empty store yields an empty JSON array with a 200."""
    resp = _client(SQLiteJobRepository(db_path=":memory:")).get("/api/jobs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_jobs_returns_camelcase_card_shape():
    """Each job serializes as the lean camelCase card contract."""
    repo = SQLiteJobRepository(db_path=":memory:")
    _seed(repo, "Senior Engineer", score=88, url="https://x/1")

    resp = _client(repo).get("/api/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1

    job = body[0]
    assert job["title"] == "Senior Engineer"
    assert job["company"] == "Acme Corp"
    assert job["platforms"] == ["linkedin"]
    assert job["score"] == 88
    assert job["threshold"] == 75
    # camelCase aliases matter — the frontend contract (ADR-033) reads these keys.
    assert job["nearMissFloor"] == 60
    assert job["hireRecommendation"] == "Yes"
    assert job["seniorityLevel"] == "Senior"
    assert "near_miss_floor" not in job


def test_list_jobs_ordered_by_score_descending():
    """The endpoint returns jobs strongest-match first."""
    repo = SQLiteJobRepository(db_path=":memory:")
    _seed(repo, "Low", score=55, url="https://x/low")
    _seed(repo, "High", score=92, url="https://x/high")
    _seed(repo, "Mid", score=70, url="https://x/mid")

    scores = [j["score"] for j in _client(repo).get("/api/jobs").json()]
    assert scores == [92, 70, 55]


# ---------------------------------------------------------------------------
# GET /api/jobs/{id} — detail fan-out (W2)
# ---------------------------------------------------------------------------


def test_get_job_detail_returns_full_shape():
    """The detail endpoint returns the breakdown, skills, status, and history."""
    repo = SQLiteJobRepository(db_path=":memory:")
    job_id = _seed(repo, "Senior Engineer", score=88, url="https://x/1")

    resp = _client(repo).get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    body = resp.json()

    assert body["id"] == job_id
    assert body["description"] == "A job."
    assert body["summary"] == "Strong fit."
    assert body["matchedSkills"] == ["python"]
    assert body["status"] == "evaluated"
    assert body["saved"] is False
    assert body["generations"] == []
    # Nine-category breakdown in rubric order, camelCase fields.
    breakdown = body["scoreBreakdown"]
    assert len(breakdown) == 9
    assert breakdown[0]["category"] == "role_alignment"
    assert breakdown[0]["earned"] == 20 and breakdown[0]["max"] == 20
    # Creation history row present.
    assert body["statusHistory"] == [
        {
            "fromStatus": None,
            "toStatus": "evaluated",
            "note": None,
            "changedAt": body["statusHistory"][0]["changedAt"],
        }
    ]


def test_get_job_detail_unknown_id_returns_404():
    """An unknown job id yields a 404."""
    resp = _client(SQLiteJobRepository(db_path=":memory:")).get("/api/jobs/999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/jobs/{id}/status — the first mutation (W2)
# ---------------------------------------------------------------------------


def test_patch_status_moves_job_and_records_history():
    """A human status write moves the job and appends a history row."""
    repo = SQLiteJobRepository(db_path=":memory:")
    job_id = _seed(repo, "Senior Engineer", score=88, url="https://x/1")

    resp = _client(repo).patch(
        f"/api/jobs/{job_id}/status", json={"status": "applied", "note": "referred"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "applied"
    transitions = [(e["fromStatus"], e["toStatus"], e["note"]) for e in body["statusHistory"]]
    assert transitions == [
        (None, "evaluated", None),
        ("evaluated", "applied", "referred"),
    ]


def test_patch_status_idempotent_no_op_adds_no_history():
    """Re-writing the current status is a no-op — no new history row."""
    repo = SQLiteJobRepository(db_path=":memory:")
    job_id = _seed(repo, "Senior Engineer", score=88, url="https://x/1")
    client = _client(repo)
    client.patch(f"/api/jobs/{job_id}/status", json={"status": "applied"})

    resp = client.patch(f"/api/jobs/{job_id}/status", json={"status": "applied"})
    assert resp.status_code == 200
    assert len(resp.json()["statusHistory"]) == 2  # creation + one applied


def test_patch_status_rejects_machine_status_with_422():
    """A machine status is not a selectable value (ui-spec §4) — 422."""
    repo = SQLiteJobRepository(db_path=":memory:")
    job_id = _seed(repo, "Senior Engineer", score=88, url="https://x/1")

    resp = _client(repo).patch(f"/api/jobs/{job_id}/status", json={"status": "evaluated"})
    assert resp.status_code == 422


def test_patch_status_unknown_id_returns_404():
    """Marking an unknown job yields a 404."""
    resp = _client(SQLiteJobRepository(db_path=":memory:")).patch(
        "/api/jobs/999/status", json={"status": "applied"}
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/jobs/{id}/saved — the bookmark toggle (W2)
# ---------------------------------------------------------------------------


def test_patch_saved_toggles_bookmark():
    """The saved endpoint flips the bookmark and never writes history."""
    repo = SQLiteJobRepository(db_path=":memory:")
    job_id = _seed(repo, "Senior Engineer", score=88, url="https://x/1")
    client = _client(repo)

    resp = client.patch(f"/api/jobs/{job_id}/saved", json={"saved": True})
    assert resp.status_code == 200
    assert resp.json()["saved"] is True
    assert len(resp.json()["statusHistory"]) == 1  # unchanged by a save

    resp = client.patch(f"/api/jobs/{job_id}/saved", json={"saved": False})
    assert resp.json()["saved"] is False


def test_patch_saved_unknown_id_returns_404():
    """Saving an unknown job yields a 404."""
    resp = _client(SQLiteJobRepository(db_path=":memory:")).patch(
        "/api/jobs/999/saved", json={"saved": True}
    )
    assert resp.status_code == 404
