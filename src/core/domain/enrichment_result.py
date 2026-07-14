"""EnrichmentResult domain entity — the pre-filter verdict for a single job."""

from pydantic import BaseModel


class EnrichmentResult(BaseModel):
    """The pre-filter's verdict on a single scraped job.

    Produced by a JobEnrichmentPort adapter before any paid evaluation. It is
    advisory: whether a flagged job is actually skipped depends on the run's
    enrichment mode (shadow measures, enforce acts). The reason is always
    recorded so a flag is never applied silently.
    """

    should_skip: bool
    """True when the pre-filter judges the job obviously irrelevant."""

    reason: str
    """Short human-readable justification for the verdict. Always populated."""

    errored: bool = False
    """True when this verdict is a fail-open fallback, not a real judgement.

    Set when the pre-filter could not actually assess the job (API error, invalid
    response, or a tripped circuit breaker). Lets the run report distinguish
    "assessed and kept" from "never assessed" so a broken pre-filter cannot
    masquerade as one that simply flagged nothing.
    """
