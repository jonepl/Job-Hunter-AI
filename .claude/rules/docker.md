# Rules — Docker

- Single all-in-one container, managed via `docker-compose`.
- Base image `python:3.10-slim`, `WORKDIR /app`. Entry point is
  `CMD ["python", "-m", "src.main"]`.
- Playwright browser binaries are installed inside the container
  (`playwright install --with-deps`).
- Secrets are injected at runtime via `env_file: .env` — never baked into the
  image.
- Three volume mounts persist state outside the container:
  - `./docs/resume:/app/docs/resume` — resume PDF input
  - `./output:/app/output` — CSV results output
  - `./logs:/app/logs` — application logs
- `restart: unless-stopped` keeps the container alive for scheduled
  (APScheduler) execution.
- For task-level Docker guidance, see `.claude/skills/docker/SKILL.md`.
