"""File output adapter — saves results to a timestamped CSV file."""

import csv
import logging
import os
from datetime import datetime

from src.core.domain.run_report import RunReport
from src.core.ports.output_port import OutputPort

logger = logging.getLogger(__name__)

_CSV_FIELDS = [
    "result_type",
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
    "run_at",
    "query",
    "search_location",
    "score_threshold",
    "top_results_cap",
]


class FileOutput(OutputPort):
    """Saves a run report to a timestamped CSV file. Always writes — even on zero results."""

    def __init__(self, output_dir: str = "output") -> None:
        """Initialise the file output adapter.

        Args:
            output_dir: Directory where CSV result files are written.
                        Defaults to "output". Created if it does not exist.
        """
        self._output_dir = output_dir

    async def deliver(self, report: RunReport) -> None:
        """Write a run report to a timestamped CSV file.

        Always writes a file regardless of whether qualifying results exist.
        When qualifying results exist the filename is results_<timestamp>.csv.
        When zero qualifying results the filename is no_results_<timestamp>.csv
        and the file contains the near-miss rows instead.

        Args:
            report: RunReport produced by the pipeline this run.
        """
        os.makedirs(self._output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        top_results_cap_label = str(report.top_results) if report.top_results is not None else "not set"
        run_at_iso = report.run_at.isoformat()

        if report.has_qualifying_results:
            rows_to_write = report.qualifying_results
            result_type_label = "qualifying"
            path = os.path.join(self._output_dir, f"results_{timestamp}.csv")
        else:
            rows_to_write = report.near_miss_results
            result_type_label = "near_miss"
            path = os.path.join(self._output_dir, f"no_results_{timestamp}.csv")

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
                writer.writeheader()
                for rank, result in enumerate(rows_to_write, start=1):
                    bd = result.score_breakdown
                    writer.writerow({
                        "result_type": result_type_label,
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
                        "run_at": run_at_iso,
                        "query": report.query,
                        "search_location": report.location,
                        "score_threshold": report.score_threshold,
                        "top_results_cap": top_results_cap_label,
                    })

            if report.has_qualifying_results:
                logger.info("FileOutput — results written to %s", path)
            else:
                logger.info(
                    "FileOutput — zero results report written to %s — %d near-misses included",
                    path,
                    len(report.near_miss_results),
                )
        except OSError as exc:
            logger.error("FileOutput — failed to write CSV: %s", exc)
        except Exception as exc:
            logger.error("FileOutput — unexpected error: %s", exc)
