"""Unit tests for the RunCost and EvaluationCost domain models."""

import pytest

from src.core.domain.run_cost import EvaluationCost, RunCost


def _make_eval(
    job_title: str = "Engineer",
    company: str = "Acme",
    input_tokens: int = 1000,
    output_tokens: int = 200,
    cost_usd: float = 0.005,
) -> EvaluationCost:
    """Return an EvaluationCost with defaults."""
    return EvaluationCost(
        job_title=job_title,
        company=company,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )


def test_from_evaluations_sums_correctly():
    """from_evaluations correctly sums input tokens, output tokens, and cost."""
    evals = [
        _make_eval(input_tokens=1000, output_tokens=200, cost_usd=0.010),
        _make_eval(input_tokens=2000, output_tokens=300, cost_usd=0.020),
        _make_eval(input_tokens=1500, output_tokens=250, cost_usd=0.015),
    ]
    run_cost = RunCost.from_evaluations(evals, provider="openai")

    assert run_cost.total_input_tokens == 4500
    assert run_cost.total_output_tokens == 750
    assert run_cost.total_cost_usd == pytest.approx(0.045)
    assert run_cost.jobs_evaluated == 3
    assert run_cost.provider == "openai"


def test_formatted_total_four_decimal_places():
    """formatted_total returns total cost to four decimal places."""
    evals = [_make_eval(cost_usd=0.2134)]
    run_cost = RunCost.from_evaluations(evals, provider="anthropic")
    assert run_cost.formatted_total == "$0.2134"


def test_from_evaluations_empty_list():
    """from_evaluations with empty list produces all-zero RunCost."""
    run_cost = RunCost.from_evaluations([], provider="openai")

    assert run_cost.total_input_tokens == 0
    assert run_cost.total_output_tokens == 0
    assert run_cost.total_cost_usd == 0.0
    assert run_cost.jobs_evaluated == 0
    assert run_cost.evaluations == []
