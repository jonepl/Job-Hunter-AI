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
    "title",
    "company",
    "location",
    "platform",
    "score",
    "matched_skills",
    "missing_skills",
    "summary",
    "url",
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
                    writer.writerow({
                        "rank": rank,
                        "title": result.job.title,
                        "company": result.job.company,
                        "location": result.job.location,
                        "platform": result.job.platform,
                        "score": result.score,
                        "matched_skills": "; ".join(result.matched_skills),
                        "missing_skills": "; ".join(result.missing_skills),
                        "summary": result.summary,
                        "url": result.job.url,
                        "scraped_at": result.job.scraped_at.isoformat(),
                    })
            logger.info("FileOutput — results written to %s", path)
        except OSError as exc:
            logger.error("FileOutput — failed to write CSV: %s", exc)
        except Exception as exc:
            logger.error("FileOutput — unexpected error: %s", exc)
