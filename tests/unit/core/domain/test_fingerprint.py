"""Unit tests for the deterministic job fingerprint (ADR-024, §13).

The fingerprint is a pure function, so it is tested as a table of raw -> canonical
pairs plus match / near-miss / distinct triples. The design bias is toward
splitting: substantive qualifiers and levels stay distinct, and a field that
normalizes to empty disables dedup rather than merging on a partial key.
"""

import pytest

from src.core.domain.fingerprint import (
    FINGERPRINT_VERSION,
    Fingerprint,
    _normalize_company,
    _normalize_location,
    _normalize_title,
    compute_fingerprint,
    relation,
)

# ---------------------------------------------------------------------------
# Company normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Acme Corp Inc", "acme"),
        ("Acme, Inc.", "acme"),
        ("Acme LLC", "acme"),
        ("McDonald's", "mcdonalds"),
        ("Café Corp", "cafe"),
        ("AT&T", "at and t"),
        ("Acme (formerly Beta)", "acme"),
        ("Acme via LinkedIn", "acme"),
        ("Corporation Street Ltd", "corporation street"),  # trailing-only suffix strip
        ("  ACME   corp  ", "acme"),
        ("", ""),
    ],
)
def test_normalize_company(raw, expected):
    """Company normalization matches the §13 canonical form."""
    assert _normalize_company(raw) == expected


# ---------------------------------------------------------------------------
# Title normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Sr. Software Engineer", "senior software engineer"),
        ("Software Engineer III", "software engineer 3"),
        ("Software Engineer", "software engineer"),
        ("Senior SWE (Backend)", "senior software engineer backend"),
        ("Senior SWE (Frontend)", "senior software engineer frontend"),
        ("Backend Engineer - Remote", "backend engineer"),
        ("Full-Time Python Developer", "python developer"),
        ("Python Developer (m/f/d)", "python developer"),
        ("Urgent Hiring!! Data Engineer", "data engineer"),
        ("Sr Mgr, Data", "senior manager data"),
        ("Staff Engineer | Hybrid", "staff engineer"),
        ("", ""),
    ],
)
def test_normalize_title(raw, expected):
    """Title normalization matches the §13 canonical form, order preserved."""
    assert _normalize_title(raw) == expected


def test_title_preserves_token_order():
    """Tokens are never sorted — order carries meaning."""
    assert _normalize_title("Data Engineer") != _normalize_title("Engineer Data")


# ---------------------------------------------------------------------------
# Location normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Remote", "remote us"),
        ("US Remote", "remote us"),
        ("Anywhere", "remote us"),
        ("New York, NY, United States", "new york ny"),
        ("California, United States", "ca"),
        ("California", "ca"),
        ("CA", "ca"),
        ("USA", "us"),
        ("U.S.", "us"),
        ("United States", "us"),
        ("NYC", "new york"),
        ("Austin, TX", "austin tx"),
        ("", ""),
    ],
)
def test_normalize_location(raw, expected):
    """Location normalization matches the §13 canonical form."""
    assert _normalize_location(raw) == expected


def test_california_and_abbrev_converge():
    """Full single-word state name and its abbreviation canonicalize identically."""
    assert _normalize_location("California") == _normalize_location("CA")


# ---------------------------------------------------------------------------
# compute_fingerprint and the key
# ---------------------------------------------------------------------------


def test_compute_fingerprint_builds_key():
    """A complete fingerprint yields a pipe-joined canonical key with the version."""
    fp = compute_fingerprint("Acme Corp Inc", "Sr. Software Engineer", "Remote")
    assert fp.canon_company == "acme"
    assert fp.canon_title == "senior software engineer"
    assert fp.canon_location == "remote us"
    assert fp.key == "acme|senior software engineer|remote us"
    assert fp.version == FINGERPRINT_VERSION
    assert fp.is_complete is True


@pytest.mark.parametrize(
    "company, title, location",
    [
        ("", "Engineer", "Remote"),
        ("Acme", "", "Remote"),
        ("Acme", "Engineer", "!!!"),  # location normalizes to empty
    ],
)
def test_incomplete_fingerprint_disables_dedup(company, title, location):
    """Any field empty after normalization yields a None key (dedup disabled)."""
    fp = compute_fingerprint(company, title, location)
    assert fp.key is None
    assert fp.is_complete is False


# ---------------------------------------------------------------------------
# Relation: match / near-miss / distinct
# ---------------------------------------------------------------------------


def test_relation_match():
    """Identical canonical fields across three raw variants are a match."""
    a = compute_fingerprint("Acme Corp", "Sr Software Engineer", "Remote")
    b = compute_fingerprint("ACME, Inc.", "Senior SWE", "US Remote")
    assert relation(a, b) == "match"


def test_relation_near_miss_on_location():
    """Same company + title, different location is a near-miss (never merged)."""
    a = compute_fingerprint("Acme", "Software Engineer", "New York, NY")
    b = compute_fingerprint("Acme", "Software Engineer", "Austin, TX")
    assert relation(a, b) == "near_miss"


def test_relation_distinct_on_title_level():
    """A level qualifier keeps two jobs distinct (bias toward splitting)."""
    a = compute_fingerprint("Acme", "Software Engineer", "Remote")
    b = compute_fingerprint("Acme", "Software Engineer III", "Remote")
    assert relation(a, b) == "distinct"


def test_relation_distinct_on_backend_frontend():
    """Substantive qualifiers stay distinct — (Backend) != (Frontend)."""
    a = compute_fingerprint("Acme", "Engineer (Backend)", "Remote")
    b = compute_fingerprint("Acme", "Engineer (Frontend)", "Remote")
    assert relation(a, b) == "distinct"


def test_relation_incomplete_is_distinct():
    """An incomplete fingerprint never matches — dedup is disabled for it."""
    a = compute_fingerprint("", "Engineer", "Remote")
    b = compute_fingerprint("", "Engineer", "Remote")
    assert relation(a, b) == "distinct"


def test_fingerprint_is_pydantic_model():
    """Fingerprint is a Pydantic model (domain entities are never plain dicts)."""
    assert isinstance(compute_fingerprint("Acme", "Engineer", "Remote"), Fingerprint)
