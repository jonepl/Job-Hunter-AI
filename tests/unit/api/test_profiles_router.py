"""Unit tests for the /api/profiles router (W7).

Drives the profile CRUD endpoints in-process via FastAPI's TestClient against a real
SettingsService over in-memory repositories, injected through a dependency override.
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.adapters.repository.sqlite_profile_repository import (
    SQLiteProfileRepository,
)
from src.adapters.repository.sqlite_settings_repository import (
    SQLiteSettingsRepository,
)
from src.api.deps import get_settings_service
from src.api.main import create_app
from src.core.services.settings_service import SettingsService
from src.orchestration.scheduler import set_scheduler_manager


def _client(monkeypatch) -> TestClient:
    """Return a TestClient whose settings service is over empty in-memory repos."""
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)
    service = SettingsService(
        SQLiteSettingsRepository(db_path=":memory:"),
        SQLiteProfileRepository(db_path=":memory:"),
    )
    app = create_app()
    app.dependency_overrides[get_settings_service] = lambda: service
    return TestClient(app)


_REMOTE_PROFILE = {"name": "Backend", "query": "SWE", "workTypes": ["remote"]}


def test_create_and_list_profile(monkeypatch):
    """POST creates a profile (201) that GET then lists."""
    client = _client(monkeypatch)
    created = client.post("/api/profiles", json=_REMOTE_PROFILE)
    assert created.status_code == 201
    body = created.json()
    assert body["id"] >= 1
    assert body["location"] == "United States"  # remote-only resolves the default

    listed = client.get("/api/profiles").json()
    assert [p["id"] for p in listed] == [body["id"]]


def test_create_rejects_missing_location_for_non_remote(monkeypatch):
    """A non-remote profile without a location is a 400."""
    resp = _client(monkeypatch).post(
        "/api/profiles", json={"query": "SWE", "workTypes": ["hybrid"]}
    )
    assert resp.status_code == 400


def test_update_profile(monkeypatch):
    """PUT updates an existing profile."""
    client = _client(monkeypatch)
    pid = client.post("/api/profiles", json=_REMOTE_PROFILE).json()["id"]
    resp = client.put(
        f"/api/profiles/{pid}",
        json={**_REMOTE_PROFILE, "name": "Renamed", "scoreThreshold": 80},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["scoreThreshold"] == 80


def test_update_unknown_profile_returns_404(monkeypatch):
    """Updating a missing id is a 404."""
    resp = _client(monkeypatch).put("/api/profiles/999", json=_REMOTE_PROFILE)
    assert resp.status_code == 404


def test_delete_profile(monkeypatch):
    """DELETE removes a non-last profile (204)."""
    client = _client(monkeypatch)
    client.post("/api/profiles", json={**_REMOTE_PROFILE, "name": "A"})
    b = client.post("/api/profiles", json={**_REMOTE_PROFILE, "name": "B"}).json()
    resp = client.delete(f"/api/profiles/{b['id']}")
    assert resp.status_code == 204
    assert len(client.get("/api/profiles").json()) == 1


def test_delete_last_profile_returns_409(monkeypatch):
    """Deleting the last remaining profile is refused (409)."""
    client = _client(monkeypatch)
    pid = client.post("/api/profiles", json=_REMOTE_PROFILE).json()["id"]
    resp = client.delete(f"/api/profiles/{pid}")
    assert resp.status_code == 409


def test_delete_unknown_profile_returns_404(monkeypatch):
    """Deleting a missing id is a 404."""
    resp = _client(monkeypatch).delete("/api/profiles/999")
    assert resp.status_code == 404


def test_created_profile_exposes_enabled_and_last_run_fields(monkeypatch):
    """A newly created profile is enabled, with null last-run metadata."""
    client = _client(monkeypatch)
    body = client.post("/api/profiles", json=_REMOTE_PROFILE).json()
    assert body["enabled"] is True
    assert body["lastRunAt"] is None
    assert body["lastRunStatus"] is None


def test_put_can_pause_and_resume_a_profile(monkeypatch):
    """PUT with enabled:false pauses; enabled:true resumes — it round-trips."""
    client = _client(monkeypatch)
    pid = client.post("/api/profiles", json=_REMOTE_PROFILE).json()["id"]

    paused = client.put(f"/api/profiles/{pid}", json={**_REMOTE_PROFILE, "enabled": False})
    assert paused.status_code == 200
    assert paused.json()["enabled"] is False

    resumed = client.put(f"/api/profiles/{pid}", json={**_REMOTE_PROFILE, "enabled": True})
    assert resumed.json()["enabled"] is True


def test_profile_in_ignores_read_only_last_run_fields(monkeypatch):
    """last-run fields are read-only — a client can't set them through ProfileIn."""
    client = _client(monkeypatch)
    body = client.post(
        "/api/profiles",
        json={**_REMOTE_PROFILE, "lastRunStatus": "succeeded", "lastRunAt": "2026-01-01T00:00:00"},
    ).json()
    assert body["lastRunStatus"] is None
    assert body["lastRunAt"] is None


def test_new_profile_is_unscheduled_by_default(monkeypatch):
    """A newly created profile carries the unscheduled schedule defaults."""
    body = _client(monkeypatch).post("/api/profiles", json=_REMOTE_PROFILE).json()
    assert body["scheduleEnabled"] is False
    assert body["scheduleCron"] == ""
    assert body["scheduleTimezone"] == "UTC"


def test_put_can_set_a_profile_schedule(monkeypatch):
    """PUT round-trips the per-profile schedule fields."""
    client = _client(monkeypatch)
    pid = client.post("/api/profiles", json=_REMOTE_PROFILE).json()["id"]
    resp = client.put(
        f"/api/profiles/{pid}",
        json={
            **_REMOTE_PROFILE,
            "scheduleCron": "0 8 * * 1-5",
            "scheduleTimezone": "America/New_York",
            "scheduleEnabled": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["scheduleCron"] == "0 8 * * 1-5"
    assert body["scheduleTimezone"] == "America/New_York"
    assert body["scheduleEnabled"] is True


def test_crud_reconciles_the_live_scheduler(monkeypatch):
    """Create / update / delete each call manager.sync() when a scheduler is registered."""
    manager = MagicMock()
    set_scheduler_manager(manager)
    try:
        client = _client(monkeypatch)
        a = client.post("/api/profiles", json={**_REMOTE_PROFILE, "name": "A"}).json()
        client.post("/api/profiles", json={**_REMOTE_PROFILE, "name": "B"})
        assert manager.sync.call_count == 2  # one per create

        client.put(f"/api/profiles/{a['id']}", json={**_REMOTE_PROFILE, "name": "A2"})
        assert manager.sync.call_count == 3  # update reconciles too

        client.delete(f"/api/profiles/{a['id']}")
        assert manager.sync.call_count == 4  # delete reconciles too
    finally:
        set_scheduler_manager(None)
