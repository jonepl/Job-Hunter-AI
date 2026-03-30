"""JobSearchService — core orchestrator for the job search pipeline."""

import asyncio
import logging
from datetime import datetime

import PyPDF2

from src.core.domain.date_posted import DatePosted
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume
from src.core.domain.run_report import RunReport
from src.core.domain.scraper_name import ScraperName
from src.core.domain.work_type import WorkType
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
        top_results: int | None = None,
        work_types: set[WorkType] | None = None,
        date_posted: DatePosted | None = None,
        active_scrapers: list[ScraperName] | None = None,
    ) -> RunReport:
        """Execute the full job search pipeline.

        Steps:
            1. Parse resume from PDF.
            2. Scrape all platforms concurrently.
            3. Evaluate each job against the resume.
            4. Sort all evaluated results by score descending.
            5. Filter qualifying results above score threshold.
            6. Apply TOP_RESULTS cap if set.
            7. If zero qualifying — collect top 5 near-misses below threshold.
            8. Build RunReport.
            9. Deliver RunReport to all output adapters.
            10. Return RunReport.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            threshold: Minimum match score to include in results. Defaults to 70.
            top_results: Optional cap on qualifying results delivered. When None
                         all qualifying results are returned.
            date_posted: Optional recency filter applied to all scrapers. When None
                         no date filter is applied.
            active_scrapers: List of ScraperName values that were active this run.
                             Recorded in the RunReport for reporting purposes.

        Returns:
            RunReport containing qualifying results, near-miss results, and
            run metadata.
        """
        logger.info("Pipeline started — query=%r location=%r threshold=%d", query, location, threshold)

        if date_posted:
            logger.info("Date posted filter: %s", date_posted.value)
        else:
            logger.info("Date posted filter: not set (all dates returned)")

        # Step 1 — parse resume
        resume = self._parse_resume(self._resume_path)
        logger.info("Resume parsed from %s", self._resume_path)

        # Step 2 — scrape all platforms concurrently
        work_types_list = list(work_types) if work_types else None
        scrape_tasks = [
            scraper.fetch_jobs(query, location, work_types=work_types_list, date_posted=date_posted)
            for scraper in self._scrapers
        ]
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
        evaluated: list[MatchResult] = []
        for job in all_jobs:
            try:
                result = await self._evaluator.evaluate(resume, job)
                evaluated.append(result)
                logger.info("Evaluated %r @ %r — score=%d", job.title, job.company, result.score)
            except Exception as exc:
                logger.error("Evaluation failed for %r: %s", job.title, exc)

        # Step 4 — sort all evaluated by score descending
        all_evaluated = sorted(evaluated, key=lambda r: r.score, reverse=True)

        # Step 5 — filter qualifying results above threshold
        qualifying = [r for r in all_evaluated if r.score >= threshold]

        # Step 6 — apply TOP_RESULTS cap only when set
        if top_results is not None:
            pre_cap_count = len(qualifying)
            qualifying = qualifying[:top_results]
            if pre_cap_count > top_results:
                logger.info(
                    "Top results cap applied — returning %d of %d qualifying jobs",
                    top_results,
                    pre_cap_count,
                )
            else:
                logger.info(
                    "Top results cap — not reached, returning all %d qualifying results",
                    len(qualifying),
                )
        else:
            logger.info(
                "Top results cap — not set, returning all %d qualifying results",
                len(qualifying),
            )

        # Step 7 — collect near-misses only when zero qualifying results
        near_misses: list[MatchResult] = []
        if not qualifying:
            near_misses = [r for r in all_evaluated if r.score < threshold][:5]

        # Step 8 — build RunReport
        report = RunReport(
            qualifying_results=qualifying,
            near_miss_results=near_misses,
            total_evaluated=len(evaluated),
            score_threshold=threshold,
            top_results=top_results,
            query=query,
            location=location,
            run_at=datetime.now(),
            date_posted=date_posted,
            active_scrapers=active_scrapers or [],
        )

        # Step 9 — log completion summary
        if report.has_qualifying_results:
            logger.info(
                "Pipeline complete — %d qualifying results (threshold=%d)",
                len(qualifying),
                threshold,
            )
        else:
            top_near_miss_score = near_misses[0].score if near_misses else "N/A"
            logger.warning(
                "Pipeline complete — 0 qualifying results above threshold %d. "
                "Top near-miss score: %s. Consider lowering SCORE_THRESHOLD to %s.",
                threshold,
                top_near_miss_score,
                report.suggested_threshold,
            )

        # Step 10 — deliver via all output adapters
        await asyncio.gather(*[output.deliver(report) for output in self._outputs])
        logger.info("Results delivered via %d output adapter(s)", len(self._outputs))

        return report

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
