"""EnrichmentSummary domain entity — the run-level pre-filter decision surface."""

from pydantic import BaseModel

# Minimum evaluated jobs required before a shadow run can graduate to enforce.
# Graduation criterion (ADR-022): 0 false-skips across >= 50 evaluated jobs.
GRADUATION_MIN_EVALS = 50


class EnrichmentSummary(BaseModel):
    """Aggregate pre-filter outcome for a single run — the graduation surface.

    Shadow mode is only useful if its output is a *decision surface* rather than
    log noise (ADR-022). This summary reports how many jobs the pre-filter would
    have skipped, how often it was wrong (the false-skip rate, measurable only in
    shadow mode where flagged jobs are still evaluated), and whether the written
    criterion to graduate to enforce mode has been met.
    """

    mode: str
    """Enrichment mode this run: 'shadow' or 'enforce'."""

    total_jobs: int
    """Jobs the pre-filter inspected this run."""

    flagged_count: int
    """Jobs the pre-filter flagged to skip (would-skip in shadow, did-skip in enforce)."""

    evaluated_count: int
    """Jobs actually sent to the paid evaluator this run."""

    error_count: int = 0
    """Jobs the pre-filter could not assess (fail-open fallbacks).

    A high count means the pre-filter is degraded, not that it found nothing to
    skip — flag counts and the false-skip rate are only meaningful for the jobs it
    actually assessed (total_jobs - error_count).
    """

    false_skips: int | None = None
    """Shadow only: flagged jobs that nonetheless scored at/above threshold.

    None in enforce mode, where flagged jobs are never evaluated and their true
    scores are therefore unknowable.
    """

    estimated_savings_usd: float | None = None
    """Estimated spend the pre-filter saved (enforce) or would have saved (shadow).

    None when cost tracking is disabled and no per-evaluation cost is available.
    """

    circuit_broken: bool = False
    """True when the pre-filter's quota circuit breaker tripped mid-run."""

    @property
    def false_skip_rate(self) -> float | None:
        """Fraction of flagged jobs that were actually qualifying.

        Returns None when the rate is not measurable — enforce mode, or a shadow
        run in which nothing was flagged.
        """
        if self.false_skips is None or self.flagged_count == 0:
            return None
        return self.false_skips / self.flagged_count

    @property
    def graduation_ready(self) -> bool:
        """Whether the run meets the written criterion to flip to enforce mode.

        Criterion (ADR-022): a shadow run with 0 false-skips across at least
        GRADUATION_MIN_EVALS evaluated jobs. A run in which the pre-filter errored
        on any job is never "ready" — its precision is only partially measured.
        """
        return (
            self.mode == "shadow"
            and self.false_skips == 0
            and self.error_count == 0
            and self.evaluated_count >= GRADUATION_MIN_EVALS
        )
