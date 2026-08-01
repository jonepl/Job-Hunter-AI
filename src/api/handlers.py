"""Application-level exception handlers for the web driving adapter (bug3).

Driving-adapter concern: translate a domain exception that a route does not catch
into a clean, technology-neutral HTTP response, and log the real cause
server-side. Registering handlers here keeps the routes thin (ADR-026) and covers
every current and future route in one place rather than per-route try/except.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import RepositoryError

logger = logging.getLogger(__name__)

# Technology-neutral message: no exception type, SQL, path, or traceback ever
# reaches the client. 503 signals a temporarily unreadable store (retryable).
_REPOSITORY_ERROR_DETAIL = "A storage error occurred. Please try again."


async def _handle_repository_error(request: Request, exc: RepositoryError) -> JSONResponse:
    """Map a persistence failure to a clean 503, logging the real cause once.

    The adapter has already stripped the ``sqlite3`` type (it raised
    ``RepositoryError from <sqlite3.Error>``); here we log the chained cause with
    its traceback for operators and return a generic body to the client.

    Args:
        request: The incoming request (used for the log line's path).
        exc: The repository failure, whose ``__cause__`` is the original error.

    Returns:
        A 503 JSON response with a generic ``detail`` and no internal detail.
    """
    logger.error(
        "Repository read/write failed for %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": _REPOSITORY_ERROR_DETAIL},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the app-level exception handlers on ``app``.

    Args:
        app: The FastAPI application to attach handlers to.
    """
    app.add_exception_handler(RepositoryError, _handle_repository_error)
