"""Sighting domain entity — one observation of a job on a platform.

A single job (one fingerprint) can be sighted on several platforms — the same
posting appears on LinkedIn, Indeed, Glassdoor and ZipRecruiter. The set of
sightings is the "seen on: linkedin, indeed" read model surfaced in the report.
"""

from datetime import datetime

from pydantic import BaseModel


class Sighting(BaseModel):
    """A single observation of a job on one platform at one time."""

    platform: str
    """The scraper/source name the job was seen on (e.g. "linkedin")."""

    url: str | None = None
    """The platform-specific URL for this sighting, if known."""

    seen_at: datetime
    """When this sighting was recorded."""
