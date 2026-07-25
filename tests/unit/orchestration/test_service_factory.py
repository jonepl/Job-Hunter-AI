"""Unit tests for service_factory — pre-filter/wiring + generation-service assembly."""

from unittest.mock import MagicMock, patch

from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.services.generation_service import GenerationService
from src.orchestration.service_factory import build_generation_service, build_service


def _profile() -> SearchProfile:
    """Return a minimal SearchProfile for factory tests."""
    return SearchProfile(
        profile_id=1,
        query="Engineer",
        location="Remote",
        active_scrapers=[ScraperName.LINKEDIN],
        score_threshold=75,
        date_posted=DatePosted.DAYS3,
    )


def _patched_build(**overrides):
    """Patch every collaborator build_service calls, with optional overrides.

    Patching ``build_resume_service`` is essential — otherwise the factory would
    open the real ``data/agent.db`` resume store during a unit test.
    """
    defaults = {
        "build_scrapers": [MagicMock()],
        "build_evaluator": MagicMock(),
        "build_repository": MagicMock(),
        "build_enrichment": None,
        "build_resume_service": MagicMock(),
    }
    defaults.update(overrides)
    patchers = [
        patch(f"src.orchestration.service_factory.{name}", return_value=value)
        for name, value in defaults.items()
    ]
    return patchers


def _build_with(overrides=None):
    """Run build_service under fully patched collaborators; return the service."""
    patchers = _patched_build(**(overrides or {}))
    for p in patchers:
        p.start()
    try:
        return build_service(_profile())
    finally:
        for p in patchers:
            p.stop()


def test_build_service_wires_enrichment_and_mode(monkeypatch):
    """build_service injects the pre-filter and enforce mode into the service."""
    monkeypatch.setenv("ENRICHMENT_MODE", "enforce")
    sentinel = MagicMock()
    service = _build_with({"build_enrichment": sentinel})

    assert service._enrichment is sentinel
    assert service._enrichment_mode == "enforce"


def test_build_service_wires_repository(monkeypatch):
    """build_service injects the persistence repository into the service."""
    monkeypatch.delenv("ENRICHMENT_MODE", raising=False)
    repo_sentinel = MagicMock()
    service = _build_with({"build_repository": repo_sentinel})

    assert service._repository is repo_sentinel


def test_build_service_wires_resume_service(monkeypatch):
    """build_service injects the master-resume service into the service (ADR-028)."""
    monkeypatch.delenv("ENRICHMENT_MODE", raising=False)
    resume_sentinel = MagicMock()
    service = _build_with({"build_resume_service": resume_sentinel})

    assert service._resume_service is resume_sentinel


def test_build_service_defaults_mode_to_shadow(monkeypatch):
    """An unset ENRICHMENT_MODE defaults to shadow."""
    monkeypatch.delenv("ENRICHMENT_MODE", raising=False)
    service = _build_with()

    assert service._enrichment is None
    assert service._enrichment_mode == "shadow"


def test_build_service_normalizes_invalid_mode(monkeypatch):
    """An unrecognised ENRICHMENT_MODE falls back to shadow."""
    monkeypatch.setenv("ENRICHMENT_MODE", "banana")
    service = _build_with()

    assert service._enrichment_mode == "shadow"


def test_build_generation_service_assembles_all_collaborators(monkeypatch):
    """build_generation_service wires every generation collaborator (F).

    Every builder is patched so the unit test never opens the real ``data/agent.db``
    or the provider allowlist.
    """
    monkeypatch.setenv("GENERATIONS_DIR", "data/generations")
    patchers = {
        "build_resume_tailor": MagicMock(),
        "build_cover_letter": MagicMock(),
        "build_docx_writer": MagicMock(),
        "build_generation_repository": MagicMock(),
        "build_resume_service": MagicMock(),
        "build_repository": MagicMock(),
    }
    started = [
        patch(f"src.orchestration.service_factory.{name}", return_value=value)
        for name, value in patchers.items()
    ]
    for p in started:
        p.start()
    try:
        service = build_generation_service()
    finally:
        for p in started:
            p.stop()

    assert isinstance(service, GenerationService)
    assert service._generations_dir == "data/generations"
