# Skill: Docker

## Goal
Create, configure, and manage the Docker environment for the
job search agent. This includes writing the Dockerfile,
docker-compose.yml, and configuring all volume mounts.

## Key Decisions
- Single container — all services run together
- Playwright browser binaries installed inside the container
- Secrets injected at runtime via env_file — never baked into image
- Three Docker volume mounts:
  - docs/resume/ → resume PDF input
  - output/      → CSV results output
  - logs/        → application log files

## Steps

### Writing the Dockerfile
1. Use python:3.10-slim as the base image
2. Set WORKDIR to /app
3. Install system dependencies required by Playwright:
   - Install via apt-get: curl, wget, gnupg, ca-certificates
4. Copy requirements.txt and install Python dependencies:
   - RUN pip install --no-cache-dir -r requirements.txt
5. Install Playwright browser binaries inside the container:
   - RUN playwright install --with-deps
6. Copy src/ directory into the container
7. Create output/ and logs/ directories inside the container
8. Set CMD to run the main entry point:
   - CMD ["python", "-m", "src.core.services.job_search_service"]

### Writing docker-compose.yml
1. Use version 3.9
2. Define a single service named agent
3. Set build context to current directory
4. Reference .env via env_file
5. Define three volume mounts:
   - ./docs/resume:/app/docs/resume
   - ./output:/app/output
   - ./logs:/app/logs
6. Set restart policy to no for Phase 1

### Building and Running
Build the container:
  docker-compose build

Run the agent manually:
  docker-compose run agent

View logs:
  docker-compose logs agent

### Validation Checkpoints
- Container builds without errors
- Playwright browsers install successfully inside container
- Volume mounts are accessible from inside the container
- Environment variables are loaded correctly from .env
- Agent runs end-to-end without exiting with error code

## Error Handling

| Error | Action |
|---|---|
| Playwright install fails in container | Add --with-deps flag to playwright install |
| Missing system dependency | Add to apt-get install list in Dockerfile |
| Volume mount not found | Create the directory on host before running |
| .env variables not loading | Verify env_file path in docker-compose.yml |
