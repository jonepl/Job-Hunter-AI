"""Unit tests for scheduler.run_all_profiles()."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.exceptions import ModelNotFoundError
from src.orchestration.scheduler import (
    SchedulerManager,
    get_scheduler_manager,
    run_all_profiles,
    run_scheduled_cycle,
    set_scheduler_manager,
)


def _make_profile(
    profile_id: int,
    query: str = "Engineer",
    location: str = "Remote",
    enabled: bool = True,
) -> SearchProfile:
    """Build a minimal SearchProfile for testing."""
    return SearchProfile(
        profile_id=profile_id,
        query=query,
        location=location,
        active_scrapers=[ScraperName.LINKEDIN],
        score_threshold=75,
        date_posted=DatePosted.DAYS3,
        enabled=enabled,
    )


class TestRunAllProfiles:
    """Tests for run_all_profiles()."""

    @pytest.mark.asyncio
    async def test_run_all_profiles_runs_each_profile(self):
        """run_all_profiles() calls service.run() once per profile."""
        profiles = [_make_profile(1), _make_profile(2)]

        mock_service = MagicMock()
        mock_service.run = AsyncMock(return_value=MagicMock())

        mock_factory = MagicMock(return_value=mock_service)

        await run_all_profiles(profiles, mock_factory)

        assert mock_service.run.call_count == 2

    @pytest.mark.asyncio
    async def test_run_all_profiles_continues_on_error(self):
        """run_all_profiles() catches exceptions and continues to the next profile."""
        profiles = [_make_profile(1), _make_profile(2)]

        failing_service = MagicMock()
        failing_service.run = AsyncMock(side_effect=Exception("scraper failure"))

        succeeding_service = MagicMock()
        succeeding_service.run = AsyncMock(return_value=MagicMock())

        call_count = 0

        def factory(profile: SearchProfile):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return failing_service
            return succeeding_service

        await run_all_profiles(profiles, factory)

        assert succeeding_service.run.call_count == 1

    @pytest.mark.asyncio
    async def test_run_all_profiles_aborts_on_model_not_found(self):
        """A ModelNotFoundError aborts the trigger without running later profiles."""
        profiles = [_make_profile(1), _make_profile(2)]

        failing_service = MagicMock()
        failing_service.run = AsyncMock(side_effect=ModelNotFoundError("model 'gpt-4oo' not found"))
        second_service = MagicMock()
        second_service.run = AsyncMock(return_value=MagicMock())

        services = [failing_service, second_service]

        def factory(profile: SearchProfile):
            return services.pop(0)

        # The daemon stays up (no exception propagates) but breaks out early.
        await run_all_profiles(profiles, factory)

        failing_service.run.assert_called_once()
        second_service.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_all_profiles_skips_disabled_profiles(self, caplog):
        """A paused profile is never built or run, and the skip count is logged."""
        import logging

        profiles = [_make_profile(1, enabled=False), _make_profile(2, enabled=True)]

        mock_service = MagicMock()
        mock_service.run = AsyncMock(return_value=MagicMock())
        factory = MagicMock(return_value=mock_service)

        with caplog.at_level(logging.INFO, logger="src.orchestration.scheduler"):
            await run_all_profiles(profiles, factory)

        # The factory is built only for the enabled profile.
        assert factory.call_count == 1
        assert factory.call_args.args[0].profile_id == 2
        assert "Skipping 1 paused profile(s)" in " ".join(caplog.messages)

    @pytest.mark.asyncio
    async def test_run_all_profiles_stamps_last_run_running_then_succeeded(self):
        """Each run stamps the profile last-run running → succeeded via the settings service."""
        profiles = [_make_profile(1)]
        mock_service = MagicMock()
        mock_service.run = AsyncMock(return_value=MagicMock())
        settings_service = MagicMock()

        await run_all_profiles(profiles, MagicMock(return_value=mock_service), settings_service)

        statuses = [c.args[1] for c in settings_service.set_profile_last_run.call_args_list]
        assert statuses == ["running", "succeeded"]

    @pytest.mark.asyncio
    async def test_run_all_profiles_stamps_last_run_failed_on_error(self):
        """A profile that raises is stamped running → failed."""
        profiles = [_make_profile(1)]
        failing = MagicMock()
        failing.run = AsyncMock(side_effect=Exception("boom"))
        settings_service = MagicMock()

        await run_all_profiles(profiles, MagicMock(return_value=failing), settings_service)

        statuses = [c.args[1] for c in settings_service.set_profile_last_run.call_args_list]
        assert statuses == ["running", "failed"]

    @pytest.mark.asyncio
    async def test_run_all_profiles_logs_profile_details(self, caplog):
        """run_all_profiles() logs INFO messages with profile query and location."""
        import logging

        profiles = [_make_profile(1, query="Senior Engineer", location="United States")]

        mock_service = MagicMock()
        mock_service.run = AsyncMock(return_value=MagicMock())
        mock_factory = MagicMock(return_value=mock_service)

        with caplog.at_level(logging.INFO, logger="src.orchestration.scheduler"):
            await run_all_profiles(profiles, mock_factory)

        log_text = " ".join(caplog.messages)
        assert "Senior Engineer" in log_text
        assert "United States" in log_text


class TestRunScheduledCycle:
    """Tests for run_scheduled_cycle() — the per-fire refresh + run."""

    @pytest.mark.asyncio
    async def test_reloads_settings_and_profiles_then_runs(self):
        """The cycle applies DB settings and runs the freshly loaded profiles."""
        profiles = [_make_profile(1), _make_profile(2)]
        settings_service = MagicMock()
        settings_service.list_profiles.return_value = profiles

        factory = MagicMock()
        with (
            patch(
                "src.orchestration.service_factory.build_settings_service",
                return_value=settings_service,
            ),
            patch("src.orchestration.scheduler.run_all_profiles", new=AsyncMock()) as mock_run,
        ):
            await run_scheduled_cycle(factory)

        settings_service.apply_to_environment.assert_called_once()
        mock_run.assert_awaited_once_with(profiles, factory, settings_service)

    @pytest.mark.asyncio
    async def test_skips_when_no_profiles(self):
        """With no configured profiles the cycle returns without running."""
        settings_service = MagicMock()
        settings_service.list_profiles.return_value = []

        with (
            patch(
                "src.orchestration.service_factory.build_settings_service",
                return_value=settings_service,
            ),
            patch("src.orchestration.scheduler.run_all_profiles", new=AsyncMock()) as mock_run,
        ):
            await run_scheduled_cycle(MagicMock())

        mock_run.assert_not_awaited()


class TestSchedulerManager:
    """Tests for the in-process BackgroundScheduler wrapper (ADR-032)."""

    def test_start_registers_job_and_starts(self):
        """start() builds a BackgroundScheduler, adds the job, and starts it."""
        fake = MagicMock()
        with patch("src.orchestration.scheduler.BackgroundScheduler", return_value=fake):
            manager = SchedulerManager()
            manager.start("0 8 * * 1-5", "UTC")

        fake.add_job.assert_called_once()
        assert fake.add_job.call_args.kwargs["id"] == SchedulerManager._JOB_ID
        fake.start.assert_called_once()

    def test_reschedule_repoints_the_job(self):
        """reschedule() calls reschedule_job with a new trigger when running."""
        fake = MagicMock()
        fake.running = True
        with patch("src.orchestration.scheduler.BackgroundScheduler", return_value=fake):
            manager = SchedulerManager()
            manager.start("0 8 * * 1-5", "UTC")
            manager.reschedule("30 6 * * *", "America/New_York")

        fake.reschedule_job.assert_called_once()
        assert fake.reschedule_job.call_args.args[0] == SchedulerManager._JOB_ID

    def test_reschedule_before_start_is_noop(self):
        """reschedule() on an unstarted manager does nothing and does not raise."""
        SchedulerManager().reschedule("0 8 * * 1-5", "UTC")

    def test_shutdown_stops_and_clears(self):
        """shutdown() stops a running scheduler and leaves the manager not running."""
        fake = MagicMock()
        fake.running = True
        with patch("src.orchestration.scheduler.BackgroundScheduler", return_value=fake):
            manager = SchedulerManager()
            manager.start("0 8 * * 1-5", "UTC")
            manager.shutdown()

        fake.shutdown.assert_called_once()
        assert manager.running is False


class TestSchedulerManagerSingleton:
    """The process-wide manager accessor used by the API lifespan + router."""

    def test_set_get_and_clear(self):
        """set/get expose the singleton; clearing returns it to None."""
        assert get_scheduler_manager() is None
        manager = SchedulerManager()
        set_scheduler_manager(manager)
        try:
            assert get_scheduler_manager() is manager
        finally:
            set_scheduler_manager(None)
        assert get_scheduler_manager() is None
