"""Unit tests for the per-profile scheduler (per-profile-scheduling feature)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.exceptions import ModelNotFoundError, NoProfilesError, RunInProgressError
from src.orchestration.scheduler import (
    SchedulerManager,
    _job_id,
    _profile_id_from_job_id,
    get_scheduler_manager,
    run_all_profiles,
    set_scheduler_manager,
)


def _make_profile(
    profile_id: int,
    query: str = "Engineer",
    location: str = "Remote",
    enabled: bool = True,
    schedule_cron: str = "",
    schedule_timezone: str = "UTC",
    schedule_enabled: bool = False,
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
        schedule_cron=schedule_cron,
        schedule_timezone=schedule_timezone,
        schedule_enabled=schedule_enabled,
    )


class TestRunAllProfiles:
    """Tests for run_all_profiles() — still the sequential multi-profile runner."""

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
    async def test_run_all_profiles_reports_failures_to_caller(self):
        """A failing profile is returned in `failures` (not just logged); others report.

        This is the Bug 2 fix: the runner swallows per-profile errors for batch
        resilience, but must hand them back so the run status can be derived.
        """
        profiles = [_make_profile(1), _make_profile(2)]

        failing_service = MagicMock()
        failing_service.run = AsyncMock(side_effect=RuntimeError("scraper failure"))
        succeeding_service = MagicMock()
        succeeding_service.run = AsyncMock(return_value=MagicMock())

        services = [failing_service, succeeding_service]

        def factory(profile: SearchProfile):
            return services.pop(0)

        reports, failures = await run_all_profiles(profiles, factory)

        assert len(reports) == 1  # the successful profile still produced a report
        assert failures == [(1, "RuntimeError")]

    @pytest.mark.asyncio
    async def test_run_all_profiles_reports_model_not_found_failure(self):
        """A ModelNotFoundError is recorded in `failures` before aborting the trigger."""
        profiles = [_make_profile(1), _make_profile(2)]

        failing_service = MagicMock()
        failing_service.run = AsyncMock(side_effect=ModelNotFoundError("model 'x' not found"))
        second_service = MagicMock()
        second_service.run = AsyncMock(return_value=MagicMock())

        services = [failing_service, second_service]

        def factory(profile: SearchProfile):
            return services.pop(0)

        reports, failures = await run_all_profiles(profiles, factory)

        assert reports == []
        assert failures == [(1, "ModelNotFoundError")]
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


class TestJobIdHelpers:
    """The profile ↔ job-id mapping used by sync/remove."""

    def test_job_id_round_trips(self):
        """A profile id maps to a job id and back."""
        assert _job_id(7) == "profile-run-7"
        assert _profile_id_from_job_id("profile-run-7") == 7

    def test_unrelated_job_id_is_ignored(self):
        """A job id from another subsystem parses to None (never removed by sync)."""
        assert _profile_id_from_job_id("some-other-job") is None
        assert _profile_id_from_job_id("profile-run-abc") is None


class TestSchedulerManagerStart:
    """start() builds a single-worker BackgroundScheduler configured to serialize."""

    def test_start_configures_single_worker_and_job_defaults(self):
        """The scheduler uses a 1-worker executor + coalesce/max_instances/misfire grace."""
        fake = MagicMock()
        with patch("src.orchestration.scheduler.BackgroundScheduler", return_value=fake) as ctor:
            manager = SchedulerManager(MagicMock())
            manager.start()

        kwargs = ctor.call_args.kwargs
        assert "default" in kwargs["executors"]  # single ThreadPoolExecutor(1)
        assert kwargs["job_defaults"]["coalesce"] is True
        assert kwargs["job_defaults"]["max_instances"] == 1
        assert "misfire_grace_time" in kwargs["job_defaults"]
        fake.start.assert_called_once()

    def test_start_is_idempotent_while_running(self):
        """A second start() while running does not build a second scheduler."""
        fake = MagicMock()
        fake.running = True
        with patch("src.orchestration.scheduler.BackgroundScheduler", return_value=fake) as ctor:
            manager = SchedulerManager(MagicMock())
            manager.start()
            manager.start()
        ctor.assert_called_once()


class TestSchedulerManagerSync:
    """sync() reconciles one job per scheduled profile."""

    def _manager_with_fake_scheduler(self, existing_job_ids: list[str]):
        """Return a started manager whose scheduler is a MagicMock with given jobs."""
        fake = MagicMock()
        fake.running = True
        fake.get_jobs.return_value = [MagicMock(id=j) for j in existing_job_ids]
        manager = SchedulerManager(MagicMock())
        with patch("src.orchestration.scheduler.BackgroundScheduler", return_value=fake):
            manager.start()
        return manager, fake

    def test_sync_adds_job_for_scheduled_profile_only(self):
        """Only an enabled + schedule_enabled profile with a cron gets a job."""
        manager, fake = self._manager_with_fake_scheduler([])
        profiles = [
            # scheduled: enabled + schedule_enabled + cron
            _make_profile(1, schedule_cron="0 8 * * *", schedule_enabled=True),
            # schedule not enabled
            _make_profile(2, schedule_cron="0 8 * * *", schedule_enabled=False),
            # paused (enabled=False)
            _make_profile(3, enabled=False, schedule_cron="0 8 * * *", schedule_enabled=True),
            # scheduled flag on but empty cron
            _make_profile(4, schedule_enabled=True),
        ]

        manager.sync(profiles)

        added_ids = {c.kwargs["id"] for c in fake.add_job.call_args_list}
        assert added_ids == {"profile-run-1"}

    def test_sync_removes_job_for_unscheduled_profile(self):
        """A previously-scheduled profile that is now unscheduled has its job removed."""
        manager, fake = self._manager_with_fake_scheduler(["profile-run-9"])
        manager.sync([_make_profile(9, schedule_enabled=False)])
        fake.remove_job.assert_called_once_with("profile-run-9")

    def test_sync_leaves_foreign_jobs_untouched(self):
        """sync never removes a job that isn't a profile-run job."""
        manager, fake = self._manager_with_fake_scheduler(["some-other-job"])
        manager.sync([])
        fake.remove_job.assert_not_called()

    def test_sync_skips_invalid_cron_without_failing_others(self):
        """A profile with a bad cron is skipped; a valid sibling is still scheduled."""
        manager, fake = self._manager_with_fake_scheduler([])
        profiles = [
            _make_profile(1, schedule_cron="not a cron", schedule_enabled=True),
            _make_profile(2, schedule_cron="0 8 * * *", schedule_enabled=True),
        ]
        manager.sync(profiles)
        added_ids = {c.kwargs["id"] for c in fake.add_job.call_args_list}
        assert added_ids == {"profile-run-2"}

    def test_sync_is_noop_before_start(self):
        """sync() on an unstarted manager does nothing and does not raise."""
        SchedulerManager(MagicMock()).sync([_make_profile(1, schedule_enabled=True)])


class TestSchedulerManagerFire:
    """_fire() routes a scheduled fire through the shared guarded RunService."""

    def _manager(self, *, scheduled: bool = True):
        """Return a manager whose run_service reports the profile scheduled or not."""
        run_service = MagicMock()
        profile = _make_profile(1, schedule_cron="0 8 * * *", schedule_enabled=scheduled)
        run_service.settings_service.list_profiles.return_value = [profile]
        run_service.start_run.return_value = MagicMock(id="run-1")
        run_service.execute_run = MagicMock()  # asyncio.run is patched, so any return is fine
        return SchedulerManager(run_service), run_service

    def test_fire_starts_scheduled_run_and_executes(self):
        """A live scheduled fire starts a scheduled-trigger run and executes it."""
        manager, run_service = self._manager(scheduled=True)
        with patch("src.orchestration.scheduler.asyncio.run") as run:
            manager._fire(1)

        run_service.start_run.assert_called_once_with(profile_id=1, trigger="scheduled")
        run_service.execute_run.assert_called_once_with("run-1", profile_id=1)
        run.assert_called_once()

    def test_fire_skips_when_no_longer_scheduled(self):
        """A profile unscheduled between sync and fire is skipped (fresh re-check)."""
        manager, run_service = self._manager(scheduled=False)
        with patch("src.orchestration.scheduler.asyncio.run") as run:
            manager._fire(1)

        run_service.start_run.assert_not_called()
        run.assert_not_called()

    def test_fire_logs_and_skips_when_run_in_progress(self, caplog):
        """A blocked fire (run already active) logs once at INFO and never errors."""
        import logging

        manager, run_service = self._manager(scheduled=True)
        run_service.start_run.side_effect = RunInProgressError("A run (x) is already in progress.")

        with (
            patch("src.orchestration.scheduler.asyncio.run") as run,
            caplog.at_level(logging.INFO, logger="src.orchestration.scheduler"),
        ):
            manager._fire(1)  # must not raise

        run.assert_not_called()
        assert "skipped" in " ".join(caplog.messages).lower()

    def test_fire_logs_and_skips_on_no_profiles(self):
        """A NoProfilesError (profile deleted mid-flight) is swallowed cleanly."""
        manager, run_service = self._manager(scheduled=True)
        run_service.start_run.side_effect = NoProfilesError("gone")
        with patch("src.orchestration.scheduler.asyncio.run") as run:
            manager._fire(1)  # must not raise
        run.assert_not_called()


class TestSchedulerManagerShutdown:
    """shutdown() stops a running scheduler and clears it."""

    def test_shutdown_stops_and_clears(self):
        """shutdown() stops a running scheduler and leaves the manager not running."""
        fake = MagicMock()
        fake.running = True
        with patch("src.orchestration.scheduler.BackgroundScheduler", return_value=fake):
            manager = SchedulerManager(MagicMock())
            manager.start()
            manager.shutdown()

        fake.shutdown.assert_called_once()
        assert manager.running is False


class TestSchedulerManagerSingleton:
    """The process-wide manager accessor used by the API lifespan + router."""

    def test_set_get_and_clear(self):
        """set/get expose the singleton; clearing returns it to None."""
        assert get_scheduler_manager() is None
        manager = SchedulerManager(MagicMock())
        set_scheduler_manager(manager)
        try:
            assert get_scheduler_manager() is manager
        finally:
            set_scheduler_manager(None)
        assert get_scheduler_manager() is None
