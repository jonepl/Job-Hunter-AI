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
