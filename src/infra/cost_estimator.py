"""Static cost estimator for pre-run cost visibility.

Calculates estimated cost range before any API calls are made using
config values only.
"""

import os

from src.core.domain.cost_estimate import CostEstimate
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile

MIN_INPUT_TOKENS_PER_EVAL = 2_000
MAX_INPUT_TOKENS_PER_EVAL = 5_000
MIN_OUTPUT_TOKENS_PER_EVAL = 300
MAX_OUTPUT_TOKENS_PER_EVAL = 600


def estimate_run_cost(
    profile: SearchProfile,
    provider: str,
    input_cost_per_1m: float,
    output_cost_per_1m: float,
) -> CostEstimate:
    """Estimate cost range for one profile run.

    Calculates maximum possible evaluations from scraper config then
    applies min/max token estimates to produce a cost range.

    Args:
        profile: SearchProfile with scraper and threshold config.
        provider: LLM provider name (openai or anthropic).
        input_cost_per_1m: Input token cost per million tokens in USD.
        output_cost_per_1m: Output token cost per million tokens in USD.

    Returns:
        CostEstimate with predicted min/max cost range.
    """
    max_pages = int(os.getenv("JSEARCH_MAX_PAGES", "2"))
    linkedin_limit = 25

    # Calculate max jobs per platform type
    jsearch_count = sum(
        1 for name in profile.active_scrapers
        if name != ScraperName.LINKEDIN
    )
    linkedin_count = sum(
        1 for name in profile.active_scrapers
        if name == ScraperName.LINKEDIN
    )

    max_jobs = (
        jsearch_count * max_pages * 10
        + linkedin_count * linkedin_limit
    )

    def _token_cost(input_t: int, output_t: int) -> float:
        """Calculate cost for given input and output token counts."""
        return (
            (input_t / 1_000_000) * input_cost_per_1m
            + (output_t / 1_000_000) * output_cost_per_1m
        )

    est_min = _token_cost(MIN_INPUT_TOKENS_PER_EVAL, MIN_OUTPUT_TOKENS_PER_EVAL) * max_jobs
    est_max = _token_cost(MAX_INPUT_TOKENS_PER_EVAL, MAX_OUTPUT_TOKENS_PER_EVAL) * max_jobs

    return CostEstimate(
        max_jobs=max_jobs,
        est_min_cost_usd=est_min,
        est_max_cost_usd=est_max,
        provider=provider,
        input_cost_per_1m=input_cost_per_1m,
        output_cost_per_1m=output_cost_per_1m,
    )
