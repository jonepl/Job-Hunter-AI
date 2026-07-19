"""Unit tests for the /api/profiles router (W7).

Drives the profile CRUD endpoints in-process via FastAPI's TestClient against a real
SettingsService over in-memory repositories, injected through a dependency override.
"""

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
