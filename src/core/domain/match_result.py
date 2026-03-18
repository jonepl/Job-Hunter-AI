"""MatchResult domain entity."""

from pydantic import BaseModel, Field

from src.core.domain.job import Job


class MatchResult(BaseModel):
    """Represents the evaluated match between a resume and a job listing."""

    job: Job
    score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str
