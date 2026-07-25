"""FastAPI application factory — the web driving adapter.

Serves the JSON API under ``/api`` and, in a built deployment, the React SPA at
``/`` from the same origin (so production needs no CORS). In development the SPA
runs on the Vite dev server and reaches the API through Vite's proxy, so the dev
origin is allowed explicitly.

This module owns its own ``load_dotenv()`` because uvicorn imports it directly and
never runs ``src/main.py`` — config is env-driven with no shared loader.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routers import generations, jobs, profiles, resume, runs, settings
from src.orchestration.scheduler import SchedulerManager, set_scheduler_manager

logger = logging.getLogger(__name__)

_DEFAULT_DEV_ORIGIN = "http://localhost:5173"
_DEFAULT_SPA_DIST = "web/dist"
_DEFAULT_CRON = "0 8 * * 1-5"
_DEFAULT_TIMEZONE = "America/New_York"


def _maybe_start_scheduler() -> SchedulerManager | None:
    """Start the in-process scheduler when ``SCHEDULE_ENABLED=true`` (ADR-032).

    The web server co-locates uvicorn and a ``BackgroundScheduler`` in one process so
    a cron edit can reschedule it live. When scheduling is disabled this is a no-op, so
    the app boots identically for API-only / CLI-immediate use.

    Returns:
        The started manager (registered as the process singleton), or None.
    """
    if os.getenv("SCHEDULE_ENABLED", "false").lower() != "true":
        logger.info("SCHEDULE_ENABLED is not true — no in-process scheduler")
        return None

    from src.orchestration.service_factory import build_settings_service

    service = build_settings_service()
    service.apply_to_environment()
    app_settings = service.get_settings()
    cron = app_settings.schedule_cron or os.getenv("SCHEDULE_CRON", _DEFAULT_CRON)
    tz = app_settings.schedule_timezone or os.getenv("SCHEDULE_TIMEZONE", _DEFAULT_TIMEZONE)

    manager = SchedulerManager()
    manager.start(cron, tz)
    set_scheduler_manager(manager)
    return manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Own the in-process scheduler's lifecycle alongside the web server (ADR-032)."""
    manager = _maybe_start_scheduler()
    try:
        yield
    finally:
        if manager is not None:
            manager.shutdown()
            set_scheduler_manager(None)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Returns:
        A configured FastAPI app: CORS for the dev origin, the ``/api`` routers,
        and (when a built SPA exists) a static mount at ``/``.
    """
    load_dotenv()

    app = FastAPI(title="Job Hunter AI", version="1.0.0", lifespan=lifespan)

    # Dev only: the Vite dev server is a different origin. Same-origin in prod
    # (the SPA is served by this process), so this is a no-op there.
    origins = [
        o.strip()
        for o in os.getenv("CORS_ALLOW_ORIGINS", _DEFAULT_DEV_ORIGIN).split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes are registered before the SPA catch-all mount so /api wins.
    app.include_router(jobs.router, prefix="/api")
    app.include_router(resume.router, prefix="/api")
    app.include_router(generations.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(profiles.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")

    # Serve the built SPA at / when present; skip in dev (Vite serves it) so the
    # app still boots without a frontend build.
    spa_dist = os.getenv("SPA_DIST_DIR", _DEFAULT_SPA_DIST)
    if os.path.isdir(spa_dist):
        app.mount("/", StaticFiles(directory=spa_dist, html=True), name="spa")
        logger.info("Serving SPA from %s", spa_dist)
    else:
        logger.info("No SPA build at %s — API only (dev mode)", spa_dist)

    return app


app = create_app()
