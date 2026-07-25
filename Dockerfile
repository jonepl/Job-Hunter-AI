# ---- Stage 1: build the React SPA ----
FROM node:22-slim AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---- Stage 2: the Python app (serves the API + SPA; also the CLI entrypoint) ----
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Bring in the uv binary from its official image (no host install script needed)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies from the lockfile (reproducible; skips the dev group)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Run subsequent commands and the app through the uv-managed venv
ENV PATH="/app/.venv/bin:$PATH"

# Install Playwright browser binaries (used by the LinkedIn scraper on CLI runs)
RUN playwright install --with-deps

# Copy application source
COPY src/ ./src/

# Built SPA — FastAPI serves it at / (same origin as /api), so no production CORS
COPY --from=frontend /web/dist ./web/dist

# Create persistent state directories (mounted as volumes at runtime)
RUN mkdir -p output logs data

# Default: run the web server. Bind 0.0.0.0 *inside* the container; the compose
# file publishes only to 127.0.0.1 (ADR-034 §2 — a non-loopback publish would
# expose the no-auth app). CLI runs are a separate invocation, e.g.
#   docker compose run --rm agent python -m src.main --query "..."
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
