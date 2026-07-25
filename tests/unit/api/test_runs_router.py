"""Unit tests for the /api runs router (W8).

Drives the "Run search now" endpoints in-process via FastAPI's TestClient against a
real ``RunService`` wired to an in-memory run repository, a fake settings service, and
a fake ``run_all_profiles`` (no pipeline, no network). Starlette's TestClient runs the
post-response ``BackgroundTasks`` before the request returns, so a ``POST`` immediately
followed by a poll observes the completed row.
"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from src.adapters.repository.sqlite_run_repository import SQLiteRunRepository
from src.api.deps import get_run_service
from src.api.main import create_app
from src.core.domain.run_record import RunRecord
from src.core.services.run_service import RunService

_NOW = datetime(2026, 7, 19, 9, 0, 0)


class _FakeSettingsService:
    """Exposes only list_profiles + apply_to_environment, as RunService uses."""

    def __init__(self, profiles: list) -> None:
        self._profiles = profiles

    def apply_to_environment(self) -> None:
        pass

    def list_profiles(self) -> list:
        return list(self._profiles)


def _service(*, profiles: list, fail: bool = False) -> tuple[RunService, SQLiteRunRepository]:
    """Build a RunService over an in-memory repo + fakes; return both."""
    repo = SQLiteRunRepository(db_path=":memory:")

    async def fake_run_all(profs, factory, settings_service=None):
        if fail:
            raise RuntimeError("scraper exploded")
        return []

    service = RunService(
        run_repo=repo,
        settings_service=_FakeSettingsService(profiles),
        service_factory=lambda p: None,
        run_all_profiles=fake_run_all,
    )
    return service, repo


def _client(service: RunService) -> TestClient:
    """Return a TestClient whose run-service dependency is the given service."""
    app = create_app()
    app.dependency_overrides[get_run_service] = lambda: service
    return TestClient(app)


def test_post_run_starts_a_run_and_returns_202():
    """POST /runs returns 202 with the running record."""
    service, _ = _service(profiles=["p1"])
    client = _client(service)

    resp = client.post("/api/runs")

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "running"
    assert body["trigger"] == "web"
    assert body["id"]


def test_post_run_then_poll_shows_succeeded():
    """The background task completes, so a poll after POST reports succeeded."""
    service, _ = _service(profiles=["p1"])
    client = _client(service)

    run_id = client.post("/api/runs").json()["id"]
    poll = client.get(f"/api/runs/{run_id}")

    assert poll.status_code == 200
    assert poll.json()["status"] == "succeeded"


def test_post_run_returns_400_when_no_profiles():
    """POST /runs is a 400 when there is nothing to run."""
    service, _ = _service(profiles=[])
    resp = _client(service).post("/api/runs")
    assert resp.status_code == 400


def test_post_run_returns_409_when_a_run_is_already_active():
    """POST /runs is a 409 when a run is already in progress (single-flight)."""
    service, repo = _service(profiles=["p1"])
    # Pre-seed a running row so start_run sees an active run (the background task
    # from a real POST would otherwise complete and free the guard).
    repo.save(RunRecord(id="already", status="running", started_at=_NOW))

    resp = _client(service).post("/api/runs")
    assert resp.status_code == 409


def test_poll_unknown_run_returns_404():
    """Polling an unknown run id is a 404."""
    service, _ = _service(profiles=["p1"])
    resp = _client(service).get("/api/runs/nope")
    assert resp.status_code == 404


def test_list_runs_returns_history_newest_first():
    """GET /runs lists recent runs newest-first."""
    service, repo = _service(profiles=["p1"])
    repo.save(RunRecord(id="old", status="succeeded", started_at=_NOW - timedelta(hours=1)))
    repo.save(RunRecord(id="new", status="succeeded", started_at=_NOW))

    resp = _client(service).get("/api/runs")

    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert ids[:2] == ["new", "old"]


def test_failed_run_response_carries_type_name_only():
    """A failed run surfaces the exception type, never a raw message (CLAUDE.md #2)."""
    service, _ = _service(profiles=["p1"], fail=True)
    client = _client(service)

    run_id = client.post("/api/runs").json()["id"]
    body = client.get(f"/api/runs/{run_id}").json()

    assert body["status"] == "failed"
    assert body["error"] == "RuntimeError"
    assert "exploded" not in body["error"]
