"""File output adapter — saves results to a timestamped CSV file."""

import csv
import logging
import os
from datetime import datetime

from src.core.domain.match_result import MatchResult
from src.core.ports.output_port import OutputPort

logger = logging.getLogger(__name__)

_CSV_FIELDS = [
    "rank",
    "score",
    "hire_recommendation",
    "seniority_level",
    "years_experience_detected",
    "job_title",
    "company",
    "location",
    "platform",
    "url",
    "summary",
    "matched_skills",
    "missing_skills",
    "role_alignment_earned",
    "role_alignment_max",
    "technical_stack_match_earned",
    "technical_stack_match_max",
    "system_design_architecture_earned",
    "system_design_architecture_max",
    "impact_and_metrics_earned",
    "impact_and_metrics_max",
    "domain_industry_experience_earned",
    "domain_industry_experience_max",
    "problem_space_relevance_earned",
    "problem_space_relevance_max",
    "ownership_and_leadership_earned",
    "ownership_and_leadership_max",
    "resume_signal_quality_earned",
    "resume_signal_quality_max",
    "career_trajectory_earned",
    "career_trajectory_max",
    "scraped_at",
]


class FileOutput(OutputPort):
    """Saves ranked job match results to a timestamped CSV file."""

    def __init__(self, output_dir: str = "output") -> None:
        """Initialise the file output adapter.

        Args:
            output_dir: Directory where CSV result files are written.
                        Defaults to "output". Created if it does not exist.
        """
        self._output_dir = output_dir

    async def deliver(self, results: list[MatchResult]) -> None:
        """Write ranked match results to a timestamped CSV file.

        Args:
            results: Ordered list of MatchResult entities to write.
        """
        if not results:
            logger.info("FileOutput — no results to write")
            return

        os.makedirs(self._output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self._output_dir, f"results_{timestamp}.csv")

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
                writer.writeheader()
                for rank, result in enumerate(results, start=1):
                    bd = result.score_breakdown
                    writer.writerow({
                        "rank": rank,
                        "score": result.score,
                        "hire_recommendation": result.hire_recommendation,
                        "seniority_level": result.seniority_level,
                        "years_experience_detected": result.years_experience_detected,
                        "job_title": result.job.title,
                        "company": result.job.company,
                        "location": result.job.location,
                        "platform": result.job.platform,
                        "url": result.job.url,
                        "summary": result.summary,
                        "matched_skills": "|".join(result.matched_skills),
                        "missing_skills": "|".join(result.missing_skills),
                        "role_alignment_earned": bd.role_alignment.earned,
                        "role_alignment_max": bd.role_alignment.max,
                        "technical_stack_match_earned": bd.technical_stack_match.earned,
                        "technical_stack_match_max": bd.technical_stack_match.max,
                        "system_design_architecture_earned": bd.system_design_architecture.earned,
                        "system_design_architecture_max": bd.system_design_architecture.max,
                        "impact_and_metrics_earned": bd.impact_and_metrics.earned,
                        "impact_and_metrics_max": bd.impact_and_metrics.max,
                        "domain_industry_experience_earned": bd.domain_industry_experience.earned,
                        "domain_industry_experience_max": bd.domain_industry_experience.max,
                        "problem_space_relevance_earned": bd.problem_space_relevance.earned,
                        "problem_space_relevance_max": bd.problem_space_relevance.max,
                        "ownership_and_leadership_earned": bd.ownership_and_leadership.earned,
                        "ownership_and_leadership_max": bd.ownership_and_leadership.max,
                        "resume_signal_quality_earned": bd.resume_signal_quality.earned,
                        "resume_signal_quality_max": bd.resume_signal_quality.max,
                        "career_trajectory_earned": bd.career_trajectory.earned,
                        "career_trajectory_max": bd.career_trajectory.max,
                        "scraped_at": result.job.scraped_at.isoformat(),
                    })
            logger.info("FileOutput — results written to %s", path)
        except OSError as exc:
            logger.error("FileOutput — failed to write CSV: %s", exc)
        except Exception as exc:
            logger.error("FileOutput — unexpected error: %s", exc)
