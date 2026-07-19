"""Unit tests for the FastAPI lifespan's in-process scheduler wiring (ADR-032).

The web server co-locates uvicorn and a BackgroundScheduler in one process. Entering
the TestClient as a context manager triggers the lifespan; these tests assert the
scheduler starts only when SCHEDULE_ENABLED=true and stops on shutdown. The scheduler
and settings service are mocked so no real thread or DB is touched.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.scheduler import get_scheduler_manager


def test_lifespan_does_not_start_scheduler_when_disabled(monkeypatch):
    """With SCHEDULE_ENABLED unset/false, no scheduler is registered on startup."""
    monkeypatch.setenv("SCHEDULE_ENABLED", "false")
    with TestClient(create_app()):
        assert get_scheduler_manager() is None


def test_lifespan_starts_and_stops_scheduler_when_enabled(monkeypatch):
    """With SCHEDULE_ENABLED=true, the scheduler starts on entry and stops on exit."""
    monkeypatch.setenv("SCHEDULE_ENABLED", "true")

    service = MagicMock()
    service.get_settings.return_value = MagicMock(
        schedule_cron="0 8 * * 1-5", schedule_timezone="UTC"
    )
    manager = MagicMock()

    with patch("src.service_factory.build_settings_service", return_value=service), patch(
        "src.api.main.SchedulerManager", return_value=manager
    ):
        with TestClient(create_app()):
            service.apply_to_environment.assert_called_once()
            manager.start.assert_called_once_with("0 8 * * 1-5", "UTC")
            assert get_scheduler_manager() is manager
        manager.shutdown.assert_called_once()

    assert get_scheduler_manager() is None
