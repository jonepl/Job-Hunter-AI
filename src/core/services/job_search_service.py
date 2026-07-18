"""JobSearchService — core orchestrator for the job search pipeline."""

import asyncio
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

import PyPDF2

from src.core.domain.date_posted import DatePosted
from src.core.domain.enrichment_summary import EnrichmentSummary
from src.core.domain.fingerprint import Fingerprint, compute_fingerprint
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume
from src.core.domain.run_cost import RunCost
from src.core.domain.run_report import RunReport
from src.core.domain.scraper_name import ScraperName
from src.core.domain.stored_job import StoredJob
from src.core.domain.work_type import WorkType
from src.core.exceptions import ModelNotFoundError
from src.core.ports.evaluator_port import EvaluatorPort
from src.core.ports.job_enrichment_port import JobEnrichmentPort
from src.core.ports.job_repository_port import JobRepositoryPort
from src.core.ports.output_port import OutputPort
from src.core.ports.scraper_port import ScraperPort

if TYPE_CHECKING:
    from src.infra.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


def _job_key(job: Job) -> tuple[str, str, str]:
    """Return a stable identity key for a job.

    Used to correlate a pre-filter flag with the job's later evaluation result.
    Object identity is unreliable because Pydantic may re-copy nested models, so
    a value key on (title, company, url) is used instead.

    Args:
        job: The job to key.

    Returns:
        A (title, company, url) tuple identifying the job within a run.
    """
    return (job.title, job.company, job.url)


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
        enrichment: JobEnrichmentPort | None = None,
        enrichment_mode: str = "shadow",
        repository: JobRepositoryPort | None = None,
    ) -> None:
        """Initialise the service with injected port adapters.

        Args:
            scrapers: List of platform scraper adapters implementing ScraperPort.
            evaluator: Resume evaluation adapter implementing EvaluatorPort.
            outputs: List of result delivery adapters implementing OutputPort.
            resume_path: Path to the candidate resume PDF file.
            enrichment: Optional pre-filter adapter implementing JobEnrichmentPort.
                        When None the pre-filter stage is skipped entirely.
            enrichment_mode: 'shadow' (evaluate everything, only measure what would
                             have been skipped) or 'enforce' (actually skip flagged
                             jobs). Ignored when enrichment is None.
            repository: Optional persistence adapter implementing
                        JobRepositoryPort. When provided, seen jobs skip
                        re-evaluation (their stored score is reused) and new
                        evaluations are persisted. When None, dedup and
                        persistence are skipped entirely.
        """
        self._scrapers = scrapers
        self._evaluator = evaluator
        self._outputs = outputs
        self._resume_path = resume_path
        self._enrichment = enrichment
        self._enrichment_mode = enrichment_mode
        self._repository = repository

    async def run(
        self,
        query: str,
        location: str,
        threshold: int = 70,
        top_results: int | None = None,
        work_types: set[WorkType] | None = None,
        date_posted: DatePosted | None = None,
        active_scrapers: list[ScraperName] | None = None,
        cost_tracker: "CostTracker | None" = None,
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
            cost_tracker: Optional CostTracker instance. When provided, token
                          usage is recorded per evaluation and a RunCost is built.

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

        # Step 2.5 — optional pre-filter. Flags obvious junk before paid evaluation.
        # Shadow mode evaluates everything and only measures what *would* have been
        # skipped; enforce mode actually withholds flagged jobs from evaluation.
        # Throttled with its own semaphore + delay so a large batch does not blow a
        # provider's per-minute quota (which the circuit breaker cannot undo once
        # every request is already in flight).
        flagged_keys: set[tuple[str, str, str]] = set()
        enrichment_error_count = 0
        if self._enrichment is not None and all_jobs:
            enrich_concurrent = int(os.getenv("ENRICHMENT_MAX_CONCURRENT", "2"))
            enrich_delay = float(os.getenv("ENRICHMENT_DELAY_SECONDS", "1.0"))
            enrich_semaphore = asyncio.Semaphore(enrich_concurrent)
            logger.info("Pre-filter concurrency : %d concurrent", enrich_concurrent)
            logger.info("Pre-filter delay       : %ss between calls", enrich_delay)

            async def enrich_with_limit(job: Job):
                """Pre-filter a single job under the semaphore, then throttle."""
                async with enrich_semaphore:
                    verdict = await self._enrichment.enrich(job)
                    await asyncio.sleep(enrich_delay)
                    return verdict

            enrich_results = await asyncio.gather(
                *[enrich_with_limit(job) for job in all_jobs]
            )
            for job, verdict in zip(all_jobs, enrich_results):
                if verdict.errored:
                    enrichment_error_count += 1
                if verdict.should_skip:
                    flagged_keys.add(_job_key(job))
            logger.info(
                "Pre-filter [%s] — %d of %d jobs flagged to skip (%d errored)",
                self._enrichment_mode,
                len(flagged_keys),
                len(all_jobs),
                enrichment_error_count,
            )

        if self._enrichment is not None and self._enrichment_mode == "enforce":
            jobs_to_evaluate = [j for j in all_jobs if _job_key(j) not in flagged_keys]
            if flagged_keys:
                logger.info(
                    "Pre-filter [enforce] — withholding %d flagged job(s) from evaluation",
                    len(all_jobs) - len(jobs_to_evaluate),
                )
        else:
            jobs_to_evaluate = all_jobs

        # Step 2.6 — deduplicate against the store and within this run.
        # A job whose fingerprint is already stored reuses its score (no re-pay);
        # the same posting seen on several platforms this run is grouped so it is
        # evaluated once and recorded as multiple sightings ("seen on: …").
        near_miss_band = int(os.getenv("NEAR_MISS_BAND", "15"))
        now = datetime.now()
        if self._repository is not None:
            reused_results, pending_groups = self._dedup_partition(jobs_to_evaluate, now)
            jobs_for_eval = [group_jobs[0] for _, group_jobs in pending_groups]
            if reused_results:
                logger.info(
                    "Dedup — reused %d stored evaluation(s); %d new job(s) to evaluate",
                    len(reused_results),
                    len(jobs_for_eval),
                )
        else:
            reused_results = []
            pending_groups = None
            jobs_for_eval = jobs_to_evaluate

        # Step 3 — evaluate each job against the resume with semaphore-controlled concurrency
        max_concurrent = int(os.getenv("MAX_CONCURRENT_EVALUATIONS", "2"))
        evaluation_delay = float(os.getenv("EVALUATION_DELAY_SECONDS", "1.0"))
        semaphore = asyncio.Semaphore(max_concurrent)
        logger.info("Evaluation concurrency : %d concurrent", max_concurrent)
        logger.info("Evaluation delay       : %ss between calls", evaluation_delay)

        async def evaluate_with_limit(job: Job) -> MatchResult | None:
            """Evaluate a single job with semaphore-controlled concurrency."""
            async with semaphore:
                try:
                    result, input_tokens, output_tokens = (
                        await self._evaluator.evaluate(
                            resume,
                            job,
                            work_types=work_types_list,
                        )
                    )
                    await asyncio.sleep(evaluation_delay)
                    if cost_tracker:
                        eval_cost = cost_tracker.record(
                            job_title=job.title,
                            company=job.company,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                        )
                        if eval_cost:
                            logger.info(
                                "Evaluated '%s' @ '%s' — score=%d"
                                " | tokens=%d/%d | cost=%s",
                                job.title,
                                job.company,
                                result.score,
                                input_tokens,
                                output_tokens,
                                f"${eval_cost.cost_usd:.4f}",
                            )
                    else:
                        logger.info(
                            "Evaluated '%s' @ '%s' — score=%d",
                            job.title,
                            job.company,
                            result.score,
                        )
                    return result
                except ModelNotFoundError:
                    # Fatal configuration error — the model is wrong for every
                    # job, so abort the run instead of zeroing out each result.
                    raise
                except Exception as exc:
                    logger.error("Evaluation failed for %r: %s", job.title, exc)
                    return None

        eval_results = await asyncio.gather(
            *[evaluate_with_limit(job) for job in jobs_for_eval]
        )

        # Step 3.5 — persist each new evaluation and attach its "seen on" set.
        # Results align with jobs_for_eval (gather preserves order), which aligns
        # with pending_groups when a repository is in use.
        new_results: list[MatchResult] = []
        for i, result in enumerate(eval_results):
            if result is None:
                continue
            if self._repository is not None and pending_groups is not None:
                fp, group_jobs = pending_groups[i]
                near_miss_floor = max(0, threshold - near_miss_band)
                stored = self._repository.save_job(
                    job=group_jobs[0],
                    fingerprint=fp,
                    match_result=result,
                    threshold=threshold,
                    near_miss_floor=near_miss_floor,
                    seen_at=now,
                )
                for extra_job in group_jobs[1:]:
                    self._repository.record_sighting(
                        stored.id, extra_job.platform, extra_job.url, now
                    )
                seen_on = self._repository.get_seen_on(stored.id)
                result = result.model_copy(update={"seen_on": seen_on})
            new_results.append(result)

        evaluated = reused_results + new_results

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

        # Step 7 — collect near-misses only when zero qualifying results.
        # Near-miss is now the fixed band [threshold - NEAR_MISS_BAND, threshold)
        # (ADR-033), not "any job below threshold". Still capped at 5.
        near_misses: list[MatchResult] = []
        if not qualifying:
            near_miss_floor = max(0, threshold - near_miss_band)
            near_misses = [
                r for r in all_evaluated if near_miss_floor <= r.score < threshold
            ][:5]

        # Step 8 — build run cost summary
        run_cost = cost_tracker.build_run_cost() if cost_tracker else None

        # Step 8.5 — build the pre-filter decision surface (false-skip rate + savings)
        enrichment_summary = None
        if self._enrichment is not None:
            enrichment_summary = self._build_enrichment_summary(
                total_jobs=len(all_jobs),
                flagged_keys=flagged_keys,
                evaluated=evaluated,
                threshold=threshold,
                run_cost=run_cost,
                error_count=enrichment_error_count,
            )
            self._log_enrichment_summary(enrichment_summary)

        # Step 9 — build RunReport
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
            run_cost=run_cost,
            enrichment_summary=enrichment_summary,
            near_miss_band=near_miss_band,
            reused_count=len(reused_results),
        )

        # Step 10 — log completion summary
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

        # Step 11 — deliver via all output adapters
        await asyncio.gather(*[output.deliver(report) for output in self._outputs])
        logger.info("Results delivered via %d output adapter(s)", len(self._outputs))

        return report

    def _build_enrichment_summary(
        self,
        total_jobs: int,
        flagged_keys: set[tuple[str, str, str]],
        evaluated: list[MatchResult],
        threshold: int,
        run_cost: RunCost | None,
        error_count: int,
    ) -> EnrichmentSummary:
        """Build the pre-filter decision surface for the run report.

        In shadow mode flagged jobs are still evaluated, so a false-skip — a
        flagged job that nonetheless scored at/above threshold — is measurable by
        comparing the flag against the real score. In enforce mode flagged jobs
        are never evaluated, so false-skips are unknowable and left as None.

        Args:
            total_jobs: Jobs the pre-filter inspected this run.
            flagged_keys: Identity keys of jobs flagged to skip.
            evaluated: The MatchResults produced this run.
            threshold: The score threshold used this run.
            run_cost: Actual run cost, or None when cost tracking is disabled.
            error_count: Jobs the pre-filter could not assess (fail-open fallbacks).

        Returns:
            An EnrichmentSummary describing flag counts, false-skips, and savings.
        """
        flagged_count = len(flagged_keys)
        false_skips: int | None = None
        if self._enrichment_mode == "shadow":
            false_skips = sum(
                1
                for r in evaluated
                if _job_key(r.job) in flagged_keys and r.score >= threshold
            )

        estimated_savings_usd: float | None = None
        if run_cost is not None and run_cost.jobs_evaluated > 0 and flagged_count > 0:
            avg_cost = run_cost.total_cost_usd / run_cost.jobs_evaluated
            estimated_savings_usd = round(avg_cost * flagged_count, 4)

        circuit_broken = bool(getattr(self._enrichment, "circuit_broken", False))

        return EnrichmentSummary(
            mode=self._enrichment_mode,
            total_jobs=total_jobs,
            flagged_count=flagged_count,
            evaluated_count=len(evaluated),
            error_count=error_count,
            false_skips=false_skips,
            estimated_savings_usd=estimated_savings_usd,
            circuit_broken=circuit_broken,
        )

    @staticmethod
    def _log_enrichment_summary(summary: EnrichmentSummary) -> None:
        """Log the pre-filter decision surface at INFO level.

        Args:
            summary: The EnrichmentSummary built for this run.
        """
        rate = summary.false_skip_rate
        rate_label = "n/a" if rate is None else f"{rate:.0%}"
        savings = summary.estimated_savings_usd
        savings_label = "n/a" if savings is None else f"${savings:.4f}"
        logger.info(
            "Pre-filter summary [%s] — flagged=%d/%d evaluated=%d errored=%d "
            "false-skips=%s false-skip-rate=%s est-savings=%s",
            summary.mode,
            summary.flagged_count,
            summary.total_jobs,
            summary.evaluated_count,
            summary.error_count,
            "n/a" if summary.false_skips is None else summary.false_skips,
            rate_label,
            savings_label,
        )
        if summary.total_jobs > 0 and summary.error_count == summary.total_jobs:
            logger.warning(
                "Pre-filter assessed 0 of %d jobs — it was fully degraded this run "
                "(check GEMINI_MODEL / GEMINI_API_KEY and quota). Flag counts are not "
                "meaningful.",
                summary.total_jobs,
            )
        if summary.graduation_ready:
            logger.info(
                "Pre-filter — graduation criterion met (0 false-skips over %d evals). "
                "Consider setting ENRICHMENT_MODE=enforce.",
                summary.evaluated_count,
            )

    def _dedup_partition(
        self, jobs: list[Job], now: datetime
    ) -> tuple[list[MatchResult], list[tuple[Fingerprint, list[Job]]]]:
        """Split scraped jobs into reused (dedup hits) and pending (to evaluate).

        For each job:

        - **Prior-run hit** — its fingerprint is already stored with an
          evaluation: record a sighting and reuse the stored score (never
          re-evaluated). Multiple scraped jobs hitting the same stored job add
          sightings but reuse the score once.
        - **New job** — grouped by fingerprint so the same posting seen on
          several platforms this run is evaluated once; the group's near-misses
          (same company + title, different location) are logged, never merged.
        - **Dedup disabled** — a fingerprint that normalizes to empty gets its
          own group and is always evaluated fresh (ADR-024).

        Requires ``self._repository`` to be set.

        Args:
            jobs: The jobs surviving the pre-filter stage.
            now: The timestamp to record sightings with.

        Returns:
            A tuple of (reused MatchResults, pending groups). Each pending group
            is (fingerprint, jobs) whose first job is the evaluation representative.
        """
        assert self._repository is not None
        repo = self._repository

        hit_stored: dict[int, StoredJob] = {}
        groups: dict[str, list[Job]] = {}
        group_fp: dict[str, Fingerprint] = {}
        group_order: list[str] = []
        no_key_groups: list[tuple[Fingerprint, Job]] = []

        for job in jobs:
            fp = compute_fingerprint(job.company, job.title, job.location)

            if fp.key is None:
                # Incomplete fingerprint — dedup disabled, evaluate fresh.
                no_key_groups.append((fp, job))
                continue

            stored = repo.find_by_fingerprint(fp.key)
            if stored is not None and stored.match_result is not None:
                repo.record_sighting(stored.id, job.platform, job.url, now)
                hit_stored[stored.id] = stored
                continue

            # New job — accumulate by fingerprint for single evaluation this run.
            if fp.key not in groups:
                groups[fp.key] = []
                group_fp[fp.key] = fp
                group_order.append(fp.key)
                for near in repo.find_near_misses(
                    fp.canon_company, fp.canon_title, exclude_key=fp.key
                ):
                    logger.info(
                        "Near-miss (logged, not merged) — %r @ %r: "
                        "stored location %r vs new %r",
                        job.title,
                        job.company,
                        near.location,
                        job.location,
                    )
            groups[fp.key].append(job)

        reused_results: list[MatchResult] = []
        for stored in hit_stored.values():
            seen_on = repo.get_seen_on(stored.id)
            reused = stored.match_result.model_copy(update={"seen_on": seen_on})
            reused_results.append(reused)
            logger.info(
                "Dedup hit — reusing stored score %d for %r @ %r (seen on: %s)",
                reused.score,
                stored.title,
                stored.company,
                ", ".join(seen_on),
            )

        pending_groups: list[tuple[Fingerprint, list[Job]]] = [
            (group_fp[key], groups[key]) for key in group_order
        ]
        pending_groups.extend((fp, [job]) for fp, job in no_key_groups)
        return reused_results, pending_groups

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
