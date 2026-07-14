"""RunReport domain entity — summary of a single pipeline run."""

from datetime import datetime

from pydantic import BaseModel

from src.core.domain.cost_estimate import CostEstimate
from src.core.domain.date_posted import DatePosted
from src.core.domain.enrichment_summary import EnrichmentSummary
from src.core.domain.match_result import MatchResult
from src.core.domain.run_cost import RunCost
from src.core.domain.scraper_name import ScraperName


class RunReport(BaseModel):
    """Represents the full summary of a single job search pipeline run.

    Always produced regardless of whether any jobs passed the score threshold.
    When qualifying_results is empty, near_miss_results contains the top 5
    jobs that came closest to the threshold so the user can make an informed
    decision about adjusting their configuration.
    """

    qualifying_results: list[MatchResult]
    """Jobs that passed threshold and TOP_RESULTS cap. May be empty."""

    near_miss_results: list[MatchResult]
    """Top 5 jobs below threshold by score. Only populated when qualifying_results is empty."""

    total_evaluated: int
    """Total number of jobs sent to LLM evaluator."""

    score_threshold: int
    """The threshold value used this run."""

    top_results: int | None = None
    """The TOP_RESULTS cap used this run. None when TOP_RESULTS was not set."""

    date_posted: DatePosted | None = None
    """The date posted recency filter used this run. None when no filter was applied."""

    active_scrapers: list[ScraperName] = []
    """The scrapers that were active this run."""

    query: str
    """The search query used this run."""

    location: str
    """The location used this run."""

    run_at: datetime
    """Timestamp of when the run completed."""

    cost_estimate: CostEstimate | None = None
    """Pre-run static cost estimate. None when SHOW_COST_ESTIMATE=false."""

    run_cost: RunCost | None = None
    """Actual LLM cost accumulated during the run. None when SHOW_COST_ESTIMATE=false."""

    enrichment_summary: EnrichmentSummary | None = None
    """Pre-filter decision surface. None when the pre-filter did not run this run."""

    @property
    def has_qualifying_results(self) -> bool:
        """Return True if any jobs passed the score threshold this run."""
        return len(self.qualifying_results) > 0

    @property
    def suggested_threshold(self) -> int | None:
        """Suggest a lower threshold based on near-miss scores.

        Returns the floor score of near-miss results rounded down to the
        nearest 5. Returns None if near_miss_results is empty.
        """
        if self.near_miss_results:
            lowest = min(r.score for r in self.near_miss_results)
            return (lowest // 5) * 5
        return None
