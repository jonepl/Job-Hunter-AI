"""ResumeService — parse-once ingestion and retrieval of the master resume.

The single place the CLI (``resume`` subcommand), the pipeline auto-seed, and the
future ``POST /resume`` upload (W5) all route through, so parsing, hashing, and the
size guard live in exactly one spot (ADR-028). Identical bytes are never re-parsed
or duplicated — the matching stored version is simply re-activated.

The ``skill_count`` / ``role_count`` it records are **best-effort heuristics** over
the extracted text (for the provenance panel), not authoritative structured parsing
— that lands in F where it is consumed.
"""

import hashlib
import logging
import os
import re
from datetime import datetime

from src.core.domain.resume import Resume
from src.core.ports.resume_parser_port import ResumeParserPort
from src.core.ports.resume_repository_port import ResumeRepositoryPort

logger = logging.getLogger(__name__)

_DEFAULT_MAX_SIZE_BYTES = 5_000_000

# A skills-section heading, then everything up to the next ALL-CAPS/Title heading
# or a blank line. Deliberately loose — provenance counts are indicative only.
_SKILLS_HEADING = re.compile(r"^\s*(technical\s+skills|skills)\s*:?\s*$", re.IGNORECASE)
_SKILL_SPLIT = re.compile(r"[,\n•|;/]+")
# A date range (e.g. "2020 - 2024", "2019 – Present") — one per role, approximately.
_DATE_RANGE = re.compile(
    r"\b(?:19|20)\d{2}\b\s*[-–—]{1,2}\s*(?:(?:19|20)\d{2}|present|current)\b",
    re.IGNORECASE,
)


class ResumeService:
    """Ingest, cache, and retrieve the candidate's master resume."""

    def __init__(
        self,
        parser: ResumeParserPort,
        repository: ResumeRepositoryPort,
        max_size_bytes: int | None = None,
    ) -> None:
        """Wire the parser and repository the service coordinates.

        Args:
            parser: Text-extraction adapter (e.g. PyPDF2ResumeParser).
            repository: Persistence adapter for versioned resume storage.
            max_size_bytes: Upload size ceiling. When None, read from
                ``RESUME_MAX_SIZE_BYTES`` (default 5,000,000).
        """
        self._parser = parser
        self._repository = repository
        if max_size_bytes is None:
            max_size_bytes = int(os.getenv("RESUME_MAX_SIZE_BYTES", str(_DEFAULT_MAX_SIZE_BYTES)))
        self._max_size_bytes = max_size_bytes

    def ingest(self, data: bytes, filename: str) -> Resume:
        """Parse and store ``data`` as the active resume, or reuse identical bytes.

        Identical bytes (same content hash) are never re-parsed or duplicated — the
        existing version is re-activated and returned. New bytes are parsed, their
        skill/role counts estimated, and stored as a new active version.

        Args:
            data: The raw resume file bytes.
            filename: The source filename (provenance only).

        Returns:
            The now-active stored Resume.

        Raises:
            ValueError: When ``data`` exceeds the size ceiling or yields no text.
        """
        if len(data) > self._max_size_bytes:
            raise ValueError(
                f"Resume is {len(data)} bytes, over the "
                f"{self._max_size_bytes}-byte limit (RESUME_MAX_SIZE_BYTES)."
            )

        content_hash = hashlib.sha256(data).hexdigest()
        existing = self._repository.find_by_hash(content_hash)
        if existing is not None:
            self._repository.activate(existing.version)
            active = self._repository.get_active()
            assert active is not None  # just activated
            logger.info(
                "Resume bytes already stored as v%d — reactivated, not re-parsed.",
                active.version,
            )
            return active

        raw_text = self._parser.extract_text(data)
        now = datetime.now()
        resume = Resume(
            raw_text=raw_text,
            parsed_at=now,
            filename=filename,
            size_bytes=len(data),
            content_hash=content_hash,
            skill_count=self._estimate_skill_count(raw_text),
            role_count=self._estimate_role_count(raw_text),
            uploaded_at=now,
        )
        return self._repository.save_version(resume)

    def ingest_path(self, path: str) -> Resume:
        """Read a resume file from disk and ingest it (CLI + auto-seed entry).

        Args:
            path: Filesystem path to the resume document.

        Returns:
            The now-active stored Resume.

        Raises:
            FileNotFoundError: When ``path`` does not exist.
            ValueError: When the file is too large or yields no text.
        """
        with open(path, "rb") as f:
            data = f.read()
        return self.ingest(data, os.path.basename(path))

    def get_active(self) -> Resume | None:
        """Return the active stored resume, or None when the store is empty."""
        return self._repository.get_active()

    def list_versions(self) -> list[Resume]:
        """Return every stored resume version, newest first."""
        return self._repository.list_versions()

    def activate(self, version: int) -> bool:
        """Restore an earlier version as the active one; False when it is absent."""
        return self._repository.activate(version)

    @staticmethod
    def _estimate_skill_count(text: str) -> int:
        """Estimate the number of listed skills from a skills section (approximate).

        Finds a ``Skills`` / ``Technical Skills`` heading and counts the distinct
        comma/pipe/bullet-separated tokens in the lines that follow, until a blank
        line. Returns 0 when no skills section is found.

        Args:
            text: The extracted resume text.

        Returns:
            An approximate count of listed skills.
        """
        lines = text.splitlines()
        collecting = False
        tokens: set[str] = set()
        for line in lines:
            if _SKILLS_HEADING.match(line):
                collecting = True
                continue
            if collecting:
                if not line.strip():
                    break
                for token in _SKILL_SPLIT.split(line):
                    token = token.strip().lower()
                    if len(token) >= 2:
                        tokens.add(token)
        return len(tokens)

    @staticmethod
    def _estimate_role_count(text: str) -> int:
        """Estimate the number of roles by counting date ranges (approximate).

        Args:
            text: The extracted resume text.

        Returns:
            The number of ``YYYY–YYYY`` / ``YYYY–Present`` date ranges found.
        """
        return len(_DATE_RANGE.findall(text))
