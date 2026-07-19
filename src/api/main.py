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

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routers import generations, jobs, resume

logger = logging.getLogger(__name__)

_DEFAULT_DEV_ORIGIN = "http://localhost:5173"
_DEFAULT_SPA_DIST = "web/dist"


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Returns:
        A configured FastAPI app: CORS for the dev origin, the ``/api`` routers,
        and (when a built SPA exists) a static mount at ``/``.
    """
    load_dotenv()

    app = FastAPI(title="Job Hunter AI", version="1.0.0")

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
