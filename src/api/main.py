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


def _start_scheduler() -> SchedulerManager:
    """Build and start the per-profile scheduler, reconciled to the stored profiles.

    Unconditional — there is no global enable gate (``SCHEDULE_ENABLED`` is gone from
    the web path); each profile opts in individually via its own ``schedule_enabled``,
    so an all-unscheduled deployment simply registers no jobs. The scheduler shares the
    API's single ``RunService`` instance so scheduled and manual runs enforce one
    single-flight guard (per-profile-scheduling §Resolved #3).

    Returns:
        The started manager (registered as the process singleton).
    """
    from src.api.deps import get_run_service, get_settings_service

    settings_service = get_settings_service()
    settings_service.apply_to_environment()

    manager = SchedulerManager(get_run_service())
    manager.start()
    manager.sync(settings_service.list_profiles())
    set_scheduler_manager(manager)
    return manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Own the in-process scheduler's lifecycle alongside the web server (ADR-032)."""
    manager = _start_scheduler()
    try:
        yield
    finally:
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
