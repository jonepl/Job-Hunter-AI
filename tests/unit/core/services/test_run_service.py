"""Unit tests for RunService (W8).

Drives the web-run orchestrator over a real in-memory run repository, a fake
settings service (profiles + env bridge), and a fake ``run_all_profiles`` that
returns canned RunReports. No pipeline, no network. Covers the single-flight guard,
the no-profiles guard, summary aggregation on success, failure recording (type-name
only), and the timed-out-run self-heal on read.
"""

from datetime import datetime, timedelta

import pytest

from src.adapters.repository.sqlite_run_repository import SQLiteRunRepository
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.job import Job
from src.core.domain.run_record import RunRecord
from src.core.domain.run_report import RunReport
from src.core.exceptions import NoProfilesError, RunInProgressError
from src.core.services.run_service import RunService

_NOW = datetime(2026, 7, 19, 9, 0, 0)


class _FakeSettingsService:
    """Exposes only list_profiles + apply_to_environment, as RunService uses."""

    def __init__(self, profiles: list) -> None:
        self._profiles = profiles
        self.applied = 0

    def apply_to_environment(self) -> None:
        self.applied += 1

    def list_profiles(self) -> list:
        return list(self._profiles)


def _match_result(score: int) -> MatchResult:
    """Return a minimal MatchResult with the given score."""
    categories = {
        "role_alignment": ScoreCategory(max=20, earned=18, reasoning="ok"),
        "technical_stack_match": ScoreCategory(max=15, earned=13, reasoning="ok"),
        "system_design_architecture": ScoreCategory(max=15, earned=12, reasoning="ok"),
        "impact_and_metrics": ScoreCategory(max=15, earned=12, reasoning="ok"),
        "domain_industry_experience": ScoreCategory(max=10, earned=8, reasoning="ok"),
        "problem_space_relevance": ScoreCategory(max=10, earned=8, reasoning="ok"),
        "ownership_and_leadership": ScoreCategory(max=10, earned=8, reasoning="ok"),
        "resume_signal_quality": ScoreCategory(max=3, earned=2, reasoning="ok"),
        "career_trajectory": ScoreCategory(max=2, earned=1, reasoning="ok"),
    }
    return MatchResult(
        job=Job(
            title="Engineer",
            company="Acme",
            location="Remote",
            url="https://x/1",
            description="A job.",
            platform="linkedin",
            scraped_at=_NOW,
        ),
        score=score,
        matched_skills=["Python"],
        missing_skills=[],
        summary="Fit.",
        seniority_level="Senior",
        years_experience_detected=8,
        hire_recommendation="Yes",
        score_breakdown=ScoreBreakdown(**categories),
    )


def _report(*, total: int, reused: int, qualifying: int) -> RunReport:
    """Build a RunReport with the given aggregate counts."""
    return RunReport(
        qualifying_results=[_match_result(90) for _ in range(qualifying)],
        near_miss_results=[],
        total_evaluated=total,
        reused_count=reused,
        score_threshold=70,
        query="q",
        location="Remote",
        run_at=_NOW,
    )


def _service(
    profiles: list,
    reports: list[RunReport] | None = None,
    *,
    fail: bool = False,
    timeout: float = 1800.0,
) -> tuple[RunService, SQLiteRunRepository]:
    """Build a RunService over an in-memory repo + fakes; return both."""
    repo = SQLiteRunRepository(db_path=":memory:")

    async def fake_run_all(profs, factory):
        if fail:
            raise RuntimeError("SECRET scraped payload exploded")
        return reports or []

    service = RunService(
        run_repo=repo,
        settings_service=_FakeSettingsService(profiles),
        service_factory=lambda p: None,
        run_all_profiles=fake_run_all,
        run_timeout_seconds=timeout,
    )
    return service, repo


def test_start_run_creates_a_running_record():
    """start_run persists and returns a running record when a profile exists."""
    service, _ = _service(profiles=["p1"])
    run = service.start_run()
    assert run.status == "running"
    assert run.trigger == "web"


def test_start_run_raises_when_no_profiles():
    """start_run refuses to start a run with nothing to run."""
    service, _ = _service(profiles=[])
    with pytest.raises(NoProfilesError):
        service.start_run()


def test_start_run_raises_when_a_run_is_already_active():
    """start_run enforces single-flight — one run at a time."""
    service, _ = _service(profiles=["p1"])
    service.start_run()
    with pytest.raises(RunInProgressError):
        service.start_run()


@pytest.mark.asyncio
async def test_execute_run_aggregates_summary_on_success():
    """execute_run sums the per-profile reports into the run summary and succeeds."""
    reports = [
        _report(total=25, reused=5, qualifying=3),
        _report(total=15, reused=0, qualifying=2),
    ]
    service, repo = _service(profiles=["p1", "p2"], reports=reports)
    run = service.start_run()

    await service.execute_run(run.id)

    done = repo.get(run.id)
    assert done.status == "succeeded"
    assert done.profiles_run == 2
    assert done.jobs_found == 40  # 25 + 15
    assert done.new_jobs == 35  # (25-5) + (15-0)
    assert done.qualifying == 5  # 3 + 2
    assert done.finished_at is not None


@pytest.mark.asyncio
async def test_execute_run_applies_env_before_running():
    """execute_run bridges DB settings into the environment before the pipeline (ADR-035)."""
    service, repo = _service(profiles=["p1"], reports=[])
    run = service.start_run()
    await service.execute_run(run.id)
    assert service._settings_service.applied == 1


@pytest.mark.asyncio
async def test_execute_run_records_failure_type_name_only():
    """A pipeline error marks the run failed with the exception type, not its message."""
    service, repo = _service(profiles=["p1"], fail=True)
    run = service.start_run()

    await service.execute_run(run.id)

    done = repo.get(run.id)
    assert done.status == "failed"
    assert done.error == "RuntimeError"
    assert "SECRET" not in done.error
    assert done.finished_at is not None


@pytest.mark.asyncio
async def test_execute_run_ignores_a_non_running_row():
    """execute_run is a no-op when the row is already terminal or gone."""
    service, repo = _service(profiles=["p1"], reports=[])
    run = service.start_run()
    repo.update(run.model_copy(update={"status": "succeeded"}))

    await service.execute_run(run.id)  # must not flip it back / raise
    assert repo.get(run.id).status == "succeeded"


def test_get_run_flips_timed_out_running_row_to_failed():
    """A running row older than the timeout self-heals to failed on read."""
    service, repo = _service(profiles=["p1"], timeout=60.0)
    repo.save(
        RunRecord(
            id="stale", status="running", started_at=_NOW - timedelta(hours=1)
        )
    )

    healed = service.get_run("stale")
    assert healed.status == "failed"
    assert healed.error == "TimeoutError"
    # And it frees the single-flight guard for a new run.
    assert service.start_run().status == "running"


def test_recent_runs_returns_newest_first():
    """recent_runs surfaces the run history newest-first."""
    service, repo = _service(profiles=["p1"])
    first = service.start_run()
    repo.update(first.model_copy(update={"status": "succeeded"}))
    second = service.start_run()

    ids = [r.id for r in service.recent_runs()]
    assert ids[0] == second.id
    assert first.id in ids
