"""Unit tests for the CostTracker infra module."""

import pytest

from src.infra.cost_tracker import CostTracker


def make_tracker(enabled: bool = True) -> CostTracker:
    """Return a CostTracker with standard test rates."""
    return CostTracker(
        provider="openai",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
        enabled=enabled,
    )


def test_record_calculates_cost_correctly():
    """record() computes correct cost from token counts and configured rates."""
    tracker = make_tracker()

    # input: 1000/1M * 2.50 = $0.0025
    # output: 200/1M * 10.00 = $0.002
    # total: $0.0045
    eval_cost = tracker.record(
        job_title="Engineer",
        company="Acme",
        input_tokens=1000,
        output_tokens=200,
    )

    assert eval_cost is not None
    assert eval_cost.cost_usd == pytest.approx(0.0045)
    assert eval_cost.input_tokens == 1000
    assert eval_cost.output_tokens == 200
    assert eval_cost.job_title == "Engineer"
    assert eval_cost.company == "Acme"


def test_record_returns_none_when_disabled():
    """record() returns None when CostTracker is disabled."""
    tracker = make_tracker(enabled=False)
    result = tracker.record(
        job_title="Engineer",
        company="Acme",
        input_tokens=1000,
        output_tokens=200,
    )
    assert result is None


def test_build_run_cost_aggregates_all_records():
    """build_run_cost() aggregates all recorded evaluations correctly."""
    tracker = make_tracker()
    tracker.record(job_title="Job A", company="Corp A", input_tokens=1000, output_tokens=200)
    tracker.record(job_title="Job B", company="Corp B", input_tokens=2000, output_tokens=300)
    tracker.record(job_title="Job C", company="Corp C", input_tokens=1500, output_tokens=250)

    run_cost = tracker.build_run_cost()

    assert run_cost is not None
    assert run_cost.jobs_evaluated == 3
    assert run_cost.total_input_tokens == 4500
    assert run_cost.total_output_tokens == 750
    assert run_cost.provider == "openai"


def test_build_run_cost_returns_none_when_disabled():
    """build_run_cost() returns None when CostTracker is disabled."""
    tracker = make_tracker(enabled=False)
    # disabled record() calls are no-ops
    tracker.record(job_title="Engineer", company="Acme", input_tokens=1000, output_tokens=200)
    assert tracker.build_run_cost() is None


def test_build_run_cost_returns_none_when_empty():
    """build_run_cost() returns None when enabled but no evaluations recorded."""
    tracker = make_tracker(enabled=True)
    assert tracker.build_run_cost() is None
