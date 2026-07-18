"""MatchResult domain entity."""

from pydantic import BaseModel, Field

from src.core.domain.job import Job


class ScoreCategory(BaseModel):
    """Represents a single scoring category with max points, earned points, and reasoning."""

    max: int
    earned: int
    reasoning: str


class ScoreBreakdown(BaseModel):
    """Represents the full score breakdown across all evaluation categories."""

    role_alignment: ScoreCategory
    technical_stack_match: ScoreCategory
    system_design_architecture: ScoreCategory
    impact_and_metrics: ScoreCategory
    domain_industry_experience: ScoreCategory
    problem_space_relevance: ScoreCategory
    ownership_and_leadership: ScoreCategory
    resume_signal_quality: ScoreCategory
    career_trajectory: ScoreCategory


class MatchResult(BaseModel):
    """Represents the evaluated match between a resume and a job listing."""

    job: Job
    score: int = Field(ge=0, le=100)
    seniority_level: str
    years_experience_detected: int | None
    score_breakdown: ScoreBreakdown
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str
    hire_recommendation: str
    seen_on: list[str] = []
    """Distinct platforms this job was sighted on (the "seen on" read model).

    Populated by the service from the repository after dedup; evaluators leave it
    empty. Defaults to [] so the evaluator contract shape is unchanged.
    """
