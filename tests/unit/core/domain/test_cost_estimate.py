"""Unit tests for the CostEstimate domain model."""

import pytest

from src.core.domain.cost_estimate import CostEstimate


def _make_estimate(**kwargs) -> CostEstimate:
    """Return a CostEstimate with sensible defaults, overridable via kwargs."""
    defaults = dict(
        max_jobs=10,
        est_min_cost_usd=0.1234,
        est_max_cost_usd=0.5678,
        provider="openai",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
    )
    return CostEstimate(**{**defaults, **kwargs})


def test_formatted_range_four_decimal_places():
    """formatted_range returns both values to four decimal places."""
    estimate = _make_estimate(est_min_cost_usd=0.1234, est_max_cost_usd=0.5678)
    assert estimate.formatted_range == "$0.1234 - $0.5678"


def test_formatted_range_small_values():
    """formatted_range preserves four decimal places for very small costs."""
    estimate = _make_estimate(est_min_cost_usd=0.0001, est_max_cost_usd=0.0009)
    assert estimate.formatted_range == "$0.0001 - $0.0009"
