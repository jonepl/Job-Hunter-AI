"""JobSearchService — core orchestrator for the job search pipeline."""

import asyncio
import logging
from datetime import datetime

import PyPDF2

from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume
from src.core.ports.evaluator_port import EvaluatorPort
from src.core.ports.output_port import OutputPort
from src.core.ports.scraper_port import ScraperPort

logger = logging.getLogger(__name__)


class JobSearchService:
    """Orchestrates the end-to-end job search pipeline.

    Accepts all external dependencies via constructor injection so that
    the core domain logic remains fully isolated from adapters.
    """

    def __init__(
        self,
        scrapers: list[ScraperPort],
        evaluator: EvaluatorPort,
        outputs: list[OutputPort],
        resume_path: str = "docs/resume/resume.pdf",
    ) -> None:
        """Initialise the service with injected port adapters.

        Args:
            scrapers: List of platform scraper adapters implementing ScraperPort.
            evaluator: Resume evaluation adapter implementing EvaluatorPort.
            outputs: List of result delivery adapters implementing OutputPort.
            resume_path: Path to the candidate resume PDF file.
        """
        self._scrapers = scrapers
        self._evaluator = evaluator
        self._outputs = outputs
        self._resume_path = resume_path

    async def run(
        self,
        query: str,
        location: str,
        threshold: int = 70,
    ) -> list[MatchResult]:
        """Execute the full job search pipeline.

        Steps:
            1. Parse resume from PDF.
            2. Scrape all platforms concurrently.
            3. Evaluate each job against the resume.
            4. Filter results below the score threshold.
            5. Rank by score descending — return top 10.
            6. Deliver results via all output adapters.
            7. Log completion summary.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            threshold: Minimum match score to include in results. Defaults to 70.

        Returns:
            Top 10 MatchResult entities ranked by score descending.
        """
        logger.info("Pipeline started — query=%r location=%r threshold=%d", query, location, threshold)

        # Step 1 — parse resume
        resume = self._parse_resume(self._resume_path)
        logger.info("Resume parsed from %s", self._resume_path)

        # Step 2 — scrape all platforms concurrently
        scrape_tasks = [scraper.fetch_jobs(query, location) for scraper in self._scrapers]
        scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

        all_jobs = []
        for i, result in enumerate(scrape_results):
            if isinstance(result, Exception):
                logger.error("Scraper %d failed: %s", i, result)
            else:
                logger.info("Scraper %d returned %d jobs", i, len(result))
                all_jobs.extend(result)

        logger.info("Total jobs scraped: %d", len(all_jobs))

        # Step 3 — evaluate each job against the resume
        match_results: list[MatchResult] = []
        for job in all_jobs:
            try:
                result = await self._evaluator.evaluate(resume, job)
                match_results.append(result)
                logger.info("Evaluated %r — score=%d", job.title, result.score)
            except Exception as exc:
                logger.error("Evaluation failed for %r: %s", job.title, exc)

        # Step 4 — filter below threshold
        filtered = [r for r in match_results if r.score >= threshold]
        logger.info("%d results above threshold (%d)", len(filtered), threshold)

        # Step 5 — rank by score descending, cap at top 10
        ranked = sorted(filtered, key=lambda r: r.score, reverse=True)[:10]
        logger.info("Returning top %d results", len(ranked))

        # Step 6 — deliver via all output adapters
        await asyncio.gather(*[output.deliver(ranked) for output in self._outputs])
        logger.info("Results delivered via %d output adapter(s)", len(self._outputs))

        # Step 7 — log completion summary
        logger.info(
            "Pipeline complete — %d/%d jobs matched (threshold=%d)",
            len(ranked),
            len(all_jobs),
            threshold,
        )

        return ranked

    def _parse_resume(self, path: str) -> Resume:
        """Extract text from a PDF resume using PyPDF2.

        Args:
            path: File path to the candidate resume PDF.

        Returns:
            A Resume domain entity containing the extracted raw text.

        Raises:
            FileNotFoundError: If the resume PDF does not exist at the given path.
            ValueError: If the PDF contains no extractable text.
        """
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            pages = [page.extract_text() or "" for page in reader.pages]
            raw_text = "\n".join(pages).strip()

        if not raw_text:
            raise ValueError(f"No text could be extracted from resume at {path}")

        return Resume(raw_text=raw_text, parsed_at=datetime.now())
