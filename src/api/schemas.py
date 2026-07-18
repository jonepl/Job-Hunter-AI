"""Response schemas for the web API.

These are the JSON contracts the React SPA consumes — deliberately lean read
models, not the full domain entities. Fields serialize as camelCase so the
generated TypeScript matches the component contracts (e.g. ``nearMissFloor`` per
ADR-033); Python code may still populate them by their snake_case names.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.core.domain.stored_job import StoredJob


class JobSummary(BaseModel):
    """A single job as shown in the job-list screen (one JobCard).

    Carries only what a card needs: identity, the deduplicated platforms it was
    seen on, and the score/threshold/near-miss-floor the ``<ThresholdRail>`` reads
    per job. The full nine-category breakdown lives on the (later) detail endpoint.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    title: str
    company: str
    location: str
    url: str | None
    platforms: list[str]
    score: int | None
    threshold: int | None
    near_miss_floor: int | None
    hire_recommendation: str | None
    seniority_level: str | None
    last_seen_at: datetime

    @classmethod
    def from_stored_job(cls, job: StoredJob) -> "JobSummary":
        """Build a JobSummary from a persisted StoredJob.

        Args:
            job: The stored job (with its optional evaluation and seen-on set).

        Returns:
            The lean card-shaped response model.
        """
        result = job.match_result
        return cls(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            platforms=job.seen_on,
            score=result.score if result is not None else None,
            threshold=job.threshold,
            near_miss_floor=job.near_miss_floor,
            hire_recommendation=result.hire_recommendation if result is not None else None,
            seniority_level=result.seniority_level if result is not None else None,
            last_seen_at=job.last_seen_at,
        )
