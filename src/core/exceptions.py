"""Core domain exceptions shared across services and adapters.

These represent fatal configuration errors that should abort a run rather than
degrade gracefully — distinct from transient runtime failures (a flaky API
call, a malformed response) which evaluators handle by returning a default
low-score result.
"""


class ModelNotFoundError(Exception):
    """Raised when the configured evaluator model does not exist for the provider.

    A misspelled or nonexistent EVALUATOR_MODEL would otherwise fail every
    evaluation identically, producing a misleading zero-results run. Raising
    this lets the entrypoint fail fast with an actionable message instead.
    """


class GenerationError(Exception):
    """Raised when a document generation cannot start for a user-fixable reason.

    Distinct from an LLM/network failure: this signals a precondition the user
    controls — no master resume stored, or an unknown job id (F). The CLI reports
    the message and exits non-zero without writing a generation record.
    """


class RunInProgressError(Exception):
    """Raised when a web run is requested while another run is still in progress (W8).

    Only one pipeline run may execute at a time — one SQLite writer, run sequentially
    (ADR-034 §1). The API maps this to a 409 so the UI can point the user at the
    already-running run instead of starting a competing one.
    """


class NoProfilesError(Exception):
    """Raised when a web run is requested but no search profiles are configured (W8).

    A run with nothing to run would immediately "succeed" with an empty summary,
    which reads as a bug. The API maps this to a 400 pointing the user at Settings.
    """


class RepositoryError(Exception):
    """Raised when a persistence operation fails at the storage boundary (bug3).

    The technology-agnostic persistence failure. The SQLite adapter catches raw
    ``sqlite3.Error`` — corruption, a locked file, disk full, permissions, a
    migration failure on open — and re-raises this with the original chained via
    ``from exc``, so no persistence-technology type ever escapes the adapter into
    the core or a driving adapter (ports abstraction, ``.claude/rules/architecture.md``).

    Unlike the config-fatal exceptions above, this does *not* abort the process:
    a driving adapter degrades it to a clean, technology-neutral error (the API
    maps it to a 503 and logs the real cause server-side). It carries no
    user-facing message itself — that copy is the handling adapter's concern, so
    the same failure can surface differently in the web API, the CLI, or a future
    driving adapter.
    """
