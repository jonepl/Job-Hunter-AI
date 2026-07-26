"""Unit tests for the FastAPI lifespan's per-profile scheduler wiring (ADR-032).

The web server co-locates uvicorn and a BackgroundScheduler in one process. Entering
the TestClient as a context manager triggers the lifespan; these tests assert the
scheduler is **always** built (no global enable gate — per-profile-scheduling), shares
the API's RunService instance, is reconciled to the stored profiles, and stops on
shutdown. The scheduler, run service, and settings service are mocked so no real thread
or DB is touched.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.orchestration.scheduler import get_scheduler_manager


def test_lifespan_builds_starts_and_syncs_scheduler():
    """The scheduler is built with the shared RunService, started, and synced to profiles."""
    settings_service = MagicMock()
    settings_service.list_profiles.return_value = ["p1", "p2"]
    run_service = MagicMock()
    manager = MagicMock()

    with (
        patch("src.api.deps.get_settings_service", return_value=settings_service),
        patch("src.api.deps.get_run_service", return_value=run_service),
        patch("src.api.main.SchedulerManager", return_value=manager) as ctor,
    ):
        with TestClient(create_app()):
            ctor.assert_called_once_with(run_service)
            settings_service.apply_to_environment.assert_called_once()
            manager.start.assert_called_once()
            manager.sync.assert_called_once_with(["p1", "p2"])
            assert get_scheduler_manager() is manager
        manager.shutdown.assert_called_once()

    assert get_scheduler_manager() is None


def test_lifespan_ignores_schedule_enabled_env(monkeypatch):
    """SCHEDULE_ENABLED is gone from the web path — the scheduler builds regardless."""
    monkeypatch.setenv("SCHEDULE_ENABLED", "false")
    settings_service = MagicMock()
    settings_service.list_profiles.return_value = []
    manager = MagicMock()

    with (
        patch("src.api.deps.get_settings_service", return_value=settings_service),
        patch("src.api.deps.get_run_service", return_value=MagicMock()),
        patch("src.api.main.SchedulerManager", return_value=manager),
    ):
        with TestClient(create_app()):
            manager.start.assert_called_once()
            assert get_scheduler_manager() is manager

    assert get_scheduler_manager() is None
