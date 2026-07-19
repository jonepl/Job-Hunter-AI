"""Unit tests for the Generation domain entity (provenance only, no content)."""

from datetime import datetime

from src.core.domain.generation import Generation


def _generation(**overrides) -> Generation:
    """Return a minimal Generation with optional field overrides."""
    fields = {
        "id": "abc123",
        "job_id": 7,
        "kind": "resume",
        "outcome": "clean",
        "file_path": "data/generations/abc123.docx",
        "provider": "openai",
        "model": "gpt-4o",
        "created_at": datetime(2026, 7, 18, 9, 0, 0),
    }
    fields.update(overrides)
    return Generation(**fields)


def test_generation_defaults_no_repair_or_review():
    """A clean generation carries no repair note and no review locations."""
    gen = _generation()
    assert gen.repair_note == ""
    assert gen.review_locations == []


def test_generation_records_review_locations_structurally():
    """A needs_review generation records structural locations, never content."""
    gen = _generation(
        outcome="needs_review",
        review_locations=["Summary", "Experience → bullet 2"],
    )
    assert gen.review_locations == ["Summary", "Experience → bullet 2"]


def test_generation_has_no_document_text_field():
    """The entity exposes provenance only — never a document-text field (CLAUDE.md #2)."""
    field_names = set(Generation.model_fields)
    for banned in ("text", "content", "body", "raw_text", "document"):
        assert banned not in field_names
