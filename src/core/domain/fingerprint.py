"""Fingerprint — deterministic job identity for exact-match deduplication.

Identity is ``company + title + location``, each canonicalized by pure,
deterministic normalization and then compared **exactly** (ADR-024). This is
normalization, never fuzzy matching: it lowercases, strips punctuation and
accents, expands a curated abbreviation map, strips trailing legal suffixes and
known noise tokens, and canonicalizes locations — but never makes a similarity
judgement, so it can never false-merge two genuinely different jobs.

The full rule set is documented in ``docs/build/vertical-story-split.md`` §13.
``compute_fingerprint`` is a pure core-domain function with no I/O, called by
both the write path and the dedup check.

Design bias: a false *split* costs one duplicate evaluation (cents, visible); a
false *merge* makes a real job vanish (the expensive, irreversible error). Every
rule below therefore biases toward splitting.
"""

import re
import unicodedata

from pydantic import BaseModel

# Bump when the normalization rules change so stale keys can be recomputed
# instead of silently mixing key generations.
FINGERPRINT_VERSION = 1

# Trailing legal-suffix tokens stripped repeatedly from a company name
# (``Acme Corp Inc`` -> ``acme``). Trailing-only, so "Corporation Street" keeps
# its word.
_LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "co",
    "company",
    "gmbh",
    "plc",
    "sa",
    "ag",
    "pty",
    "llp",
    "lp",
}

# Curated title abbreviation expansions. Values may expand to several tokens.
_TITLE_ABBREV = {
    "sr": "senior",
    "snr": "senior",
    "jr": "junior",
    "jnr": "junior",
    "mgr": "manager",
    "dev": "developer",
    "eng": "engineer",
    "engr": "engineer",
    "swe": "software engineer",
    "sde": "software engineer",
    "ml": "machine learning",
}

# Roman-numeral seniority levels -> arabic. ``i`` is intentionally excluded
# (too ambiguous to convert safely).
_ROMAN = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6"}

# Title noise dropped wherever it appears: hype words, work-mode, EEO, and
# employment-type tokens. ``m/f/d`` and ``f/m/x`` tokenize to single letters.
_TITLE_NOISE = {
    "urgent",
    "hiring",
    "now",
    "apply",
    "immediately",
    "asap",
    "remote",
    "hybrid",
    "onsite",
    "wfh",
    "contract",
    "w2",
    "c2c",
    "m",
    "f",
    "d",
    "x",
}

# Adjacent employment-type token pairs removed as a phrase (``full-time`` and
# ``full time`` both reach here as ("full", "time")).
_TITLE_PHRASE_PAIRS = {("full", "time"), ("part", "time")}

# Remote indicators -> a single canonical remote bucket. Bare "Remote" converges
# with the app's remote-only default of "United States" (a conscious US focus).
_REMOTE_TOKENS = {"remote", "anywhere", "wfh"}
_REMOTE_BUCKET = "remote us"

# Country tokens dropped when a state is present, else collapsed to ``us``.
_COUNTRY_TOKENS = {"united", "states", "usa", "us", "america", "u", "s"}

# Small curated metro alias map (single-token keys, may expand to several).
_METRO_ALIASES = {
    "nyc": "new york",
    "sf": "san francisco",
    "philly": "philadelphia",
}

# Single-word US state names -> 2-letter abbreviation. Multi-word state names
# (``new york``, ``north carolina`` …) are deliberately left as text so a city
# spelled like a state (``New York`` city) is never eaten into its abbreviation.
_STATE_NAME_TO_ABBR = {
    "alabama": "al",
    "alaska": "ak",
    "arizona": "az",
    "arkansas": "ar",
    "california": "ca",
    "colorado": "co",
    "connecticut": "ct",
    "delaware": "de",
    "florida": "fl",
    "georgia": "ga",
    "hawaii": "hi",
    "idaho": "id",
    "illinois": "il",
    "indiana": "in",
    "iowa": "ia",
    "kansas": "ks",
    "kentucky": "ky",
    "louisiana": "la",
    "maine": "me",
    "maryland": "md",
    "massachusetts": "ma",
    "michigan": "mi",
    "minnesota": "mn",
    "mississippi": "ms",
    "missouri": "mo",
    "montana": "mt",
    "nebraska": "ne",
    "nevada": "nv",
    "ohio": "oh",
    "oklahoma": "ok",
    "oregon": "or",
    "pennsylvania": "pa",
    "tennessee": "tn",
    "texas": "tx",
    "utah": "ut",
    "vermont": "vt",
    "virginia": "va",
    "washington": "wa",
    "wisconsin": "wi",
    "wyoming": "wy",
}


def _strip_accents(text: str) -> str:
    """Return ``text`` with combining accent marks removed (NFKD fold to ASCII).

    Args:
        text: The string to fold.

    Returns:
        The string with diacritics stripped.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _normalize_company(raw: str) -> str:
    """Canonicalize a company name per §13.

    Args:
        raw: The raw company string as scraped.

    Returns:
        The canonical company token string (may be empty).
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _strip_accents(text).lower()
    # Aggregator noise: "(formerly X)" and a trailing "via <source>".
    text = re.sub(r"\(\s*formerly[^)]*\)", " ", text)
    text = re.sub(r"\bvia\b.*$", " ", text)
    text = text.replace("&", " and ")
    # Delete intra-word apostrophes so "McDonald's" -> "mcdonalds", not "mcdonald s".
    text = text.replace("'", "").replace("’", "")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    while tokens and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _drop_phrase_pairs(tokens: list[str]) -> list[str]:
    """Remove adjacent employment-type token pairs (``full time``/``part time``).

    Args:
        tokens: The title token list.

    Returns:
        The token list with recognized pairs removed.
    """
    result: list[str] = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and (tokens[i], tokens[i + 1]) in _TITLE_PHRASE_PAIRS:
            i += 2
            continue
        result.append(tokens[i])
        i += 1
    return result


def _normalize_title(raw: str) -> str:
    """Canonicalize a job title per §13, preserving token order.

    Substantive qualifiers are kept — ``(Backend)`` vs ``(Frontend)`` stay
    distinct keys and levels stay distinct (``Engineer`` vs ``Engineer III``) —
    because splitting is the cheap error.

    Args:
        raw: The raw title string as scraped.

    Returns:
        The canonical title token string (may be empty).
    """
    text = unicodedata.normalize("NFKC", raw).lower()
    # Delimiters and brackets become spaces (keeps qualifiers as separate tokens).
    text = re.sub(r"[-–—|/,()\[\]]", " ", text)
    # Strip emoji/symbols; keep alphanumerics, spaces, and + # (c++, c#).
    text = re.sub(r"[^a-z0-9\s+#]", " ", text)
    tokens = _drop_phrase_pairs(text.split())

    out: list[str] = []
    for tok in tokens:
        if tok in _TITLE_NOISE:
            continue
        if tok in _TITLE_ABBREV:
            out.extend(_TITLE_ABBREV[tok].split())
            continue
        if tok in _ROMAN:
            out.append(_ROMAN[tok])
            continue
        out.append(tok)
    return " ".join(out)


def _normalize_location(raw: str) -> str:
    """Canonicalize a location per §13.

    Detects remote, expands a small metro alias map, converts single-word US
    state names to their abbreviation, and drops or collapses country tokens.
    Multi-word state names are left as text (see ``_STATE_NAME_TO_ABBR``).

    Args:
        raw: The raw location string as scraped.

    Returns:
        The canonical location token string (may be empty).
    """
    text = unicodedata.normalize("NFKC", _strip_accents(raw)).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    if not tokens:
        return ""

    if any(tok in _REMOTE_TOKENS for tok in tokens):
        return _REMOTE_BUCKET

    # Metro aliases and single-word state names, token-wise.
    expanded: list[str] = []
    for tok in tokens:
        if tok in _METRO_ALIASES:
            expanded.extend(_METRO_ALIASES[tok].split())
        elif tok in _STATE_NAME_TO_ABBR:
            expanded.append(_STATE_NAME_TO_ABBR[tok])
        else:
            expanded.append(tok)

    # Drop country tokens (redundant when a city/state is present). A location
    # that was nothing but country tokens (``USA``, ``U.S.``) collapses to ``us``.
    without_country = [t for t in expanded if t not in _COUNTRY_TOKENS]
    result = without_country if without_country else ["us"]
    return " ".join(result)


class Fingerprint(BaseModel):
    """A canonical, exactly-comparable identity for a job.

    ``key`` is the pipe-joined canonical string used for dedup lookups; it is
    ``None`` when any canonical field is empty, which disables dedup for that job
    (re-paying once is cheaper than merging on a partial key).
    """

    canon_company: str
    canon_title: str
    canon_location: str
    version: int = FINGERPRINT_VERSION

    @property
    def is_complete(self) -> bool:
        """Return True when all three canonical fields are non-empty."""
        return bool(self.canon_company and self.canon_title and self.canon_location)

    @property
    def key(self) -> str | None:
        """Return the pipe-joined canonical key, or None when incomplete.

        Punctuation is stripped during normalization, so ``|`` is a safe
        separator. A None key means dedup is disabled for this job.
        """
        if not self.is_complete:
            return None
        return f"{self.canon_company}|{self.canon_title}|{self.canon_location}"


def compute_fingerprint(company: str, title: str, location: str) -> Fingerprint:
    """Compute the canonical fingerprint for a job's identity fields.

    Pure and deterministic — no I/O. Called by both the persistence write path
    and the dedup check so the two can never disagree.

    Args:
        company: Raw company name.
        title: Raw job title.
        location: Raw location.

    Returns:
        A Fingerprint carrying the three canonical fields and the version.
    """
    return Fingerprint(
        canon_company=_normalize_company(company),
        canon_title=_normalize_title(title),
        canon_location=_normalize_location(location),
    )


def relation(a: Fingerprint, b: Fingerprint) -> str:
    """Classify two fingerprints as ``match``, ``near_miss``, or ``distinct``.

    - **match**: all three canonical fields equal (and complete) — skip re-eval
      or add a sighting.
    - **near_miss**: canonical company and title equal, location differs — log
      with both raw locations, never auto-merge.
    - **distinct**: company or title differs, or either fingerprint is
      incomplete (dedup disabled).

    Args:
        a: The first fingerprint.
        b: The second fingerprint.

    Returns:
        One of ``"match"``, ``"near_miss"``, ``"distinct"``.
    """
    if a.is_complete and b.is_complete and a.key == b.key:
        return "match"
    if (
        a.canon_company
        and a.canon_company == b.canon_company
        and a.canon_title == b.canon_title
        and a.canon_location != b.canon_location
    ):
        return "near_miss"
    return "distinct"
