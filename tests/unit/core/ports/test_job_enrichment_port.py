"""Unit tests for JobEnrichmentPort — the pre-filter privacy boundary.

The port signature is the structural guarantee that resume/personal data can
never reach the pre-filter adapter (ADR-022). These tests fail if a future edit
widens the contract to accept a Resume.
"""

import inspect

import pytest

from src.core.domain.enrichment_result import EnrichmentResult
from src.core.domain.job import Job
from src.core.domain.resume import Resume
from src.core.ports.job_enrichment_port import JobEnrichmentPort


def test_enrich_accepts_only_job_never_resume():
    """enrich's only domain parameter is a Job — never a Resume."""
    sig = inspect.signature(JobEnrichmentPort.enrich)
    params = [p for name, p in sig.parameters.items() if name != "self"]

    # Exactly one domain parameter, annotated Job.
    assert len(params) == 1
    assert params[0].name == "job"
    assert params[0].annotation is Job

    # No parameter anywhere in the signature is a Resume.
    annotations = [p.annotation for p in sig.parameters.values()]
    assert Resume not in annotations


def test_enrich_return_annotation_is_enrichment_result():
    """enrich returns an EnrichmentResult."""
    sig = inspect.signature(JobEnrichmentPort.enrich)
    assert sig.return_annotation is EnrichmentResult


def test_cannot_instantiate_without_enrich():
    """A subclass missing enrich() fails at instantiation, not silently."""

    class Incomplete(JobEnrichmentPort):
        pass

    with pytest.raises(TypeError):
        Incomplete()


@pytest.mark.asyncio
async def test_concrete_subclass_implements_enrich(sample_job: Job):
    """A concrete subclass implementing enrich() works and returns a verdict."""

    class Keep(JobEnrichmentPort):
        async def enrich(self, job: Job) -> EnrichmentResult:
            return EnrichmentResult(should_skip=False, reason="ok")

    result = await Keep().enrich(sample_job)
    assert result.should_skip is False
