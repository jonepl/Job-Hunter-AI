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
