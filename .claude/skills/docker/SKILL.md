---
name: docker
description: >
  How this project is containerized and how to build/run/manage the container.
  Use when editing the Dockerfile or docker-compose.yml, or building/running the
  agent in Docker.
---

# Skill: Docker

## Goal

Build, configure, and run the single-container job-search agent.

## Key decisions

- Single all-in-one container managed via `docker-compose`.
- Playwright browser binaries installed inside the container.
- Secrets injected at runtime via `env_file: .env` — never baked into the image.
- Three volume mounts persist state outside the container:
  - `./docs/resume:/app/docs/resume` — resume PDF input
  - `./output:/app/output` — CSV results output
  - `./logs:/app/logs` — application logs

## Dockerfile (as-built)

- Base image `python:3.10-slim`, `WORKDIR /app`.
- `apt-get install` the system deps Playwright needs (curl, wget, gnupg,
  ca-certificates).
- `pip install --no-cache-dir -r requirements.txt`.
- `playwright install --with-deps`.
- `COPY src/ ./src/` and `mkdir -p output logs`.
- `CMD ["python", "-m", "src.main"]`.

## docker-compose.yml (as-built)

- One service, `agent`; `build: .`; `env_file: .env`.
- The three volume mounts above.
- `restart: unless-stopped` (keeps the container alive for APScheduler mode).

## Build & run

```bash
docker compose build           # build the image
docker compose run agent       # one-off immediate run
docker compose up -d           # scheduled mode (SCHEDULE_ENABLED=true)
docker compose logs -f agent   # follow logs
docker compose down            # stop
```

## Validation

- Image builds without errors; Playwright browsers install successfully.
- Volume mounts are readable/writable from inside the container.
- `.env` variables load correctly (`env_file`).

## Error handling

| Error | Action |
|---|---|
| Playwright install fails | ensure `--with-deps` on `playwright install` |
| Missing system dependency | add it to the `apt-get install` list |
| Volume mount not found | create the host directory before running |
| `.env` not loading | verify the `env_file` path in docker-compose.yml |
