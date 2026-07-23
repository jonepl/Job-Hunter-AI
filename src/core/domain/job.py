"""Job domain entity."""

from datetime import datetime

from pydantic import BaseModel


class Job(BaseModel):
    """Represents a single job listing scraped from a platform."""

    title: str
    company: str
    location: str
    url: str
    description: str
    platform: str
    scraped_at: datetime

    # Compensation, employment type, and posting age (all nullable). JSearch
    # supplies all of them; LinkedIn's public cards expose only ``posted_at``.
    # A null here is normal, not an error — every consumer must degrade.
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: str | None = None  # "YEAR" | "MONTH" | "HOUR" — as reported
    employment_type: str | None = None  # "FULLTIME" | "PARTTIME" | "CONTRACTOR" | ...
    posted_at: datetime | None = None
