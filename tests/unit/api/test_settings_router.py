"""Unit tests for the /api/settings router (W7).

Drives the settings + secrets + schedule-preview endpoints in-process via FastAPI's
TestClient against a real SettingsService over in-memory repositories, injected through
a dependency override. Asserts secrets are never returned in the clear.
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
from src.scheduler import set_scheduler_manager


def _client(monkeypatch) -> TestClient:
    """Return a TestClient whose settings service is over in-memory repos."""
    monkeypatch.setenv("EVALUATOR_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-ABCD1234")
    monkeypatch.delenv("PROFILE_COUNT", raising=False)
    monkeypatch.delenv("SEARCH_QUERY", raising=False)
    service = SettingsService(
        SQLiteSettingsRepository(db_path=":memory:"),
        SQLiteProfileRepository(db_path=":memory:"),
    )
    app = create_app()
    app.dependency_overrides[get_settings_service] = lambda: service
    return TestClient(app)


def test_get_settings_returns_globals_and_masked_secrets(monkeypatch):
    """GET returns the settings + masked secrets, never a raw key."""
    resp = _client(monkeypatch).get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["evaluatorProvider"] == "openai"
    assert body["nearMissBand"] == 15
    assert "envDefaults" in body
    names = {s["name"] for s in body["secrets"]}
    assert names == {"openai_api_key", "anthropic_api_key", "gemini_api_key"}
    assert "sk-env-ABCD1234" not in resp.text
    openai = next(s for s in body["secrets"] if s["name"] == "openai_api_key")
    assert openai["masked"] == "1234" and openai["overridden"] is False


def test_get_settings_exposes_configured_pricing(monkeypatch):
    """GET surfaces read-only pricing: both providers' rates + SHOW_COST_ESTIMATE."""
    monkeypatch.setenv("SHOW_COST_ESTIMATE", "true")
    monkeypatch.setenv("OPENAI_INPUT_COST_PER_1M", "2.50")
    monkeypatch.setenv("OPENAI_OUTPUT_COST_PER_1M", "10.00")
    body = _client(monkeypatch).get("/api/settings").json()
    pricing = body["pricing"]
    assert pricing["showCostEstimate"] is True
    assert pricing["openai"] == {"inputPer1M": 2.5, "outputPer1M": 10.0}
    assert pricing["anthropic"] == {"inputPer1M": 3.0, "outputPer1M": 15.0}


def test_put_settings_ignores_pricing(monkeypatch):
    """Pricing is read-only — a client-sent pricing block is not writable."""
    resp = _client(monkeypatch).put(
        "/api/settings",
        json={
            "evaluatorProvider": "openai",
            "scheduleCron": "0 8 * * 1-5",
            "scheduleTimezone": "UTC",
            "voice": {},
            "pricing": {
                "showCostEstimate": True,
                "openai": {"inputPer1M": 999.0, "outputPer1M": 999.0},
                "anthropic": {"inputPer1M": 999.0, "outputPer1M": 999.0},
            },
        },
    )
    assert resp.status_code == 200
    # The sent pricing is ignored; the response reflects the configured .env rates.
    assert resp.json()["pricing"]["openai"]["inputPer1M"] != 999.0


def test_put_settings_persists(monkeypatch):
    """PUT persists the editable globals and echoes them back."""
    client = _client(monkeypatch)
    resp = client.put(
        "/api/settings",
        json={
            "evaluatorProvider": "anthropic",
            "evaluatorModel": "claude-sonnet-4-5",
            "scheduleCron": "0 8 * * 1-5",
            "scheduleTimezone": "UTC",
            "enrichmentMode": "enforce",
            "voice": {"tone": "warm", "person": "implied", "styleNotes": "Be brief."},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["evaluatorProvider"] == "anthropic"
    assert body["enrichmentMode"] == "enforce"
    assert body["voice"]["tone"] == "warm"


def test_put_settings_reschedules_running_scheduler(monkeypatch):
    """A saved cron/timezone reschedules the in-process scheduler live (ADR-032)."""
    client = _client(monkeypatch)
    manager = MagicMock()
    manager.running = True
    set_scheduler_manager(manager)
    try:
        resp = client.put(
            "/api/settings",
            json={
            "evaluatorProvider": "openai",
            "scheduleCron": "30 6 * * *",
            "scheduleTimezone": "UTC",
            "voice": {},
        },
        )
    finally:
        set_scheduler_manager(None)
    assert resp.status_code == 200
    manager.reschedule.assert_called_once_with("30 6 * * *", "UTC")


def test_put_settings_skips_reschedule_when_no_scheduler(monkeypatch):
    """With no running scheduler the save still succeeds (idle process)."""
    resp = _client(monkeypatch).put(
        "/api/settings",
        json={
            "evaluatorProvider": "openai",
            "scheduleCron": "30 6 * * *",
            "scheduleTimezone": "UTC",
            "voice": {},
        },
    )
    assert resp.status_code == 200


def test_put_settings_rejects_bad_provider(monkeypatch):
    """A provider outside the allowlist is a 422 (schema Literal)."""
    resp = _client(monkeypatch).put(
        "/api/settings",
        json={"evaluatorProvider": "gemini", "voice": {}},
    )
    assert resp.status_code == 422


def test_secret_replace_and_reset(monkeypatch):
    """Replacing a secret flips overridden; deleting resets to the .env value."""
    client = _client(monkeypatch)
    put = client.put("/api/settings/secrets/openai_api_key", json={"value": "sk-db-9999"})
    assert put.status_code == 200
    assert put.json()["overridden"] is True and put.json()["masked"] == "9999"

    delete = client.delete("/api/settings/secrets/openai_api_key")
    assert delete.status_code == 200
    assert delete.json()["overridden"] is False and delete.json()["masked"] == "1234"


def test_unknown_secret_returns_404(monkeypatch):
    """Writing an unknown secret name is a 404."""
    resp = _client(monkeypatch).put("/api/settings/secrets/bogus", json={"value": "x"})
    assert resp.status_code == 404


def test_schedule_preview_and_invalid_cron(monkeypatch):
    """The preview returns fire times; an invalid cron is a 400."""
    client = _client(monkeypatch)
    ok = client.get("/api/settings/schedule/preview", params={"cron": "0 9 * * *"})
    assert ok.status_code == 200
    assert len(ok.json()["nextRuns"]) == 3

    bad = client.get("/api/settings/schedule/preview", params={"cron": "not a cron"})
    assert bad.status_code == 400
